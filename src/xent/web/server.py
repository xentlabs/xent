import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.benchmark.run_benchmark import run_benchmark
from xent.common.configuration_types import CondensedXentBenchmarkConfig
from xent.common.constants import SIMPLE_GAME_CODE
from xent.common.game_discovery import discover_packaged_games
from xent.storage.directory_storage import DirectoryBenchmarkStorage, DirectoryStorage
from xent.web.websocket_game_runner import run_websocket_game

app = FastAPI(title="XENT Web Interface")

STORAGE_DIR = Path.cwd() / "results"
storage = DirectoryStorage(STORAGE_DIR)


class ConfigRequest(BaseModel):
    config: CondensedXentBenchmarkConfig


# Serve static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    # Mount static assets
    assets_path = static_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="static")

    # Serve index.html for the root
    @app.get("/")
    async def serve_index():
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {
            "error": "Frontend not built. Run 'npm run build' in the web directory."
        }


@app.get("/api/benchmarks")
async def list_benchmarks():
    try:
        configs = await storage.list_configs()
        return [config["metadata"]["benchmark_id"] for config in configs]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list benchmarks: {str(e)}"
        ) from e


@app.get("/api/benchmarks/{benchmark_id}")
async def get_benchmark_results(benchmark_id: str):
    """Get benchmark results for a specific benchmark ID"""
    try:
        result = await storage.get_result(benchmark_id)

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Benchmark {benchmark_id} not found"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch benchmark results: {str(e)}"
        ) from e


@app.post("/api/benchmarks/{benchmark_id}/run")
async def run_benchmark_async(benchmark_id: str):
    try:
        benchmark_storage = DirectoryBenchmarkStorage(STORAGE_DIR, benchmark_id)
        await benchmark_storage.initialize()
        config = await benchmark_storage.get_config()

        if config is None:
            raise HTTPException(
                status_code=404, detail=f"Benchmark {benchmark_id} not found"
            )

        # Start benchmark execution in background (don't wait for completion)
        asyncio.create_task(run_benchmark_background(config, benchmark_storage))

        return {
            "success": True,
            "message": "Benchmark execution started",
            "benchmark_id": benchmark_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start benchmark: {str(e)}"
        ) from e


async def run_benchmark_background(config, benchmark_storage):
    """Background task to run the benchmark"""
    try:
        await run_benchmark(config, benchmark_storage, max_concurrent_games=2)
    except Exception as e:
        print(f"Background benchmark execution failed: {e}")


@app.delete("/api/benchmarks/{benchmark_id}/results")
async def delete_benchmark_results(benchmark_id: str):
    """Delete benchmark results but keep the configuration"""
    try:
        benchmark_storage = DirectoryBenchmarkStorage(STORAGE_DIR, benchmark_id)
        await benchmark_storage.initialize()

        # Verify benchmark exists
        config = await benchmark_storage.get_config()
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"Benchmark {benchmark_id} not found"
            )

        # Clear all results but keep the config
        # We need to manually delete only result files, not the config
        results_dir = benchmark_storage.results_dir
        if results_dir.exists():
            for item in results_dir.iterdir():
                if item.is_file() and item.name != "benchmark_config.json":
                    item.unlink()

        return {
            "success": True,
            "message": "Benchmark results deleted successfully",
            "benchmark_id": benchmark_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete benchmark results: {str(e)}"
        ) from e


@app.get("/api/benchmarks/{benchmark_id}/stats")
async def get_benchmark_stats(benchmark_id: str):
    """Get aggregated statistics for visualization"""
    try:
        benchmark_storage = DirectoryBenchmarkStorage(STORAGE_DIR, benchmark_id)
        await benchmark_storage.initialize()

        config = await benchmark_storage.get_config()
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"Benchmark {benchmark_id} not found"
            )

        result = await benchmark_storage.get_benchmark_results()

        expected_results = len(config["players"]) * len(config["maps"])
        actual_results = len(result["results"]) if result else 0

        is_running = await benchmark_storage.get_running_state()
        if is_running:
            status = "running"
        elif actual_results >= expected_results:
            status = "completed"
        else:
            status = "ready"

        if not result or not result["results"]:
            return {
                "status": status,
                "overall_scores": {},
                "per_game_scores": {},
                "per_game_details": {},
                "metadata": {
                    "benchmark_id": benchmark_id,
                    "num_players": len(config["players"]),
                    "num_games": len(config["games"]),
                    "num_maps": len(config["maps"]),
                    "expected_results": expected_results,
                    "actual_results": actual_results,
                },
                "config": config,
            }

        overall_scores: dict[str, float] = {}
        per_game_scores: dict[str, dict[str, float]] = {}
        per_game_details: dict[str, dict[str, Any]] = {}

        for game_result in result["results"]:
            player_id = game_result["player"]["id"]
            game_name = game_result["game_map"]["name"]
            score = game_result["score"]

            if player_id not in overall_scores:
                overall_scores[player_id] = 0
            overall_scores[player_id] += score

            if game_name not in per_game_scores:
                per_game_scores[game_name] = {}
            if player_id not in per_game_scores[game_name]:
                per_game_scores[game_name][player_id] = 0
            per_game_scores[game_name][player_id] += score

            if game_name not in per_game_details:
                per_game_details[game_name] = {
                    "code": game_result["game_map"]["code"],
                    "iterations_by_player": {},
                    "arms_by_player": {},
                    "round_scores_by_player": {},
                }

            if player_id not in per_game_details[game_name]["iterations_by_player"]:
                per_game_details[game_name]["iterations_by_player"][player_id] = []
                per_game_details[game_name]["arms_by_player"][player_id] = []
                per_game_details[game_name]["round_scores_by_player"][player_id] = []

            round_scores = []
            running_max = float("-inf")
            arms_scores = []

            for round_result in game_result.get("round_results", []):
                round_score = round_result.get("score", 0)
                round_scores.append(round_score)

                if round_score > running_max:
                    running_max = round_score
                arms_scores.append(running_max)

            per_game_details[game_name]["iterations_by_player"][player_id].extend(
                round_scores
            )
            per_game_details[game_name]["arms_by_player"][player_id].extend(arms_scores)
            per_game_details[game_name]["round_scores_by_player"][player_id].extend(
                round_scores
            )

        return {
            "status": status,
            "overall_scores": overall_scores,
            "per_game_scores": per_game_scores,
            "per_game_details": per_game_details,
            "metadata": {
                "benchmark_id": benchmark_id,
                "num_players": len(config["players"]),
                "num_games": len(config["games"]),
                "num_maps": len(config["maps"]),
                "expected_results": expected_results,
                "actual_results": actual_results,
            },
            "config": config,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get benchmark stats: {str(e)}"
        ) from e


@app.get("/api/games")
async def list_available_games():
    """Return packaged games bundled with xent as GameConfig objects."""
    try:
        games = discover_packaged_games()
        return games
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load packaged games: {str(e)}"
        ) from e


class AddPlayerRequest(BaseModel):
    players: list[dict[str, Any]]


@app.post("/api/benchmarks/{benchmark_id}/add-players")
async def add_players_to_benchmark(benchmark_id: str, request: AddPlayerRequest):
    """Add new players to an existing benchmark configuration"""
    try:
        benchmark_storage = DirectoryBenchmarkStorage(STORAGE_DIR, benchmark_id)
        await benchmark_storage.initialize()

        # Get existing config
        config = await benchmark_storage.get_config()
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"Benchmark {benchmark_id} not found"
            )

        # Check if benchmark is running
        is_running = await benchmark_storage.get_running_state()
        if is_running:
            raise HTTPException(
                status_code=400, detail="Cannot add players while benchmark is running"
            )

        # Validate new players don't duplicate existing ones
        existing_player_ids = {player["id"] for player in config["players"]}
        new_player_ids = {player["id"] for player in request.players}

        duplicates = existing_player_ids & new_player_ids
        if duplicates:
            raise HTTPException(
                status_code=400,
                detail=f"Players with these IDs already exist: {', '.join(duplicates)}",
            )

        # Add new players to config
        config["players"].extend(request.players)  # type: ignore[arg-type]

        # Update the configuration in storage
        await benchmark_storage.store_config(config)

        return {
            "success": True,
            "message": f"Successfully added {len(request.players)} player(s)",
            "benchmark_id": benchmark_id,
            "total_players": len(config["players"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add players: {str(e)}"
        ) from e


@app.post("/api/config")
async def store_config(request: ConfigRequest):
    try:
        expanded_config = expand_benchmark_config(request.config)
        await storage.add_config(expanded_config)

        return {
            "success": True,
            "benchmark_id": expanded_config["metadata"]["benchmark_id"],
            "message": "Configuration stored successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to store configuration: {str(e)}"
        ) from e


# WebSocket endpoint for interactive game play
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    code = SIMPLE_GAME_CODE
    game_task = None

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            if not isinstance(message, dict) or "type" not in message:
                await websocket.send_text("Invalid message format")
                continue
            elif message["type"] == "xent_control":
                if message["command"] == "start":
                    # Use code from message if provided, otherwise fallback to current code
                    game_code = message.get("code", code)
                    print(
                        f"Starting interactive Xent game with code: {game_code[:50]}..."
                    )

                    # Cancel any existing game first
                    if game_task and not game_task.done():
                        print("Cancelling existing game")
                        game_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await game_task

                    # Start new game
                    try:
                        game_task = asyncio.create_task(
                            run_websocket_game(websocket, game_code)
                        )
                        await game_task
                        print("Game completed successfully")
                    except asyncio.CancelledError:
                        print("Game was cancelled")
                    except Exception as e:
                        print(f"Game execution failed: {e}")
                        # Error already sent to client by run_websocket_game
                else:
                    print(f"Unknown command: {message['command']}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Always cleanup game task when WebSocket closes
        if game_task and not game_task.done():
            print("Cleaning up game task on disconnect")
            game_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await game_task
