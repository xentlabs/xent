"""API endpoints for XEGA web interface."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from xega.benchmark.expand_benchmark import expand_benchmark_config
from xega.benchmark.run_benchmark import run_benchmark
from xega.cli.cli_util import generate_benchmark_id
from xega.storage.directory_storage import DirectoryStorage
from xega.storage.storage_interface import Storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class BenchmarkStartRequest(BaseModel):
    """Request model for starting a benchmark."""
    config_path: str = "./xega_config.json"
    results_dir: str = "./results"
    parallel_games: int = 1
    regenerate_id: bool = False


class BenchmarkStartResponse(BaseModel):
    """Response model for benchmark start."""
    benchmark_id: str
    status: str
    message: str


class BenchmarkStatus(BaseModel):
    """Model for benchmark status."""
    id: str
    exists: bool
    is_running: bool
    progress: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None


# Store running benchmarks
running_benchmarks: Dict[str, asyncio.Task] = {}


async def run_benchmark_task(
    config_path: str,
    results_dir: str,
    benchmark_id: str,
    parallel_games: int
):
    """Background task to run a benchmark."""
    try:
        # Load config
        with open(config_path) as f:
            benchmark_config = json.load(f)
        
        # Set benchmark ID
        benchmark_config["metadata"]["benchmark_id"] = benchmark_id
        
        # Expand config if needed
        if benchmark_config.get("config_type") != "expanded_xega_config":
            benchmark_config = expand_benchmark_config(benchmark_config)
        
        # Create storage
        storage: Storage = DirectoryStorage(results_dir, benchmark_id)
        await storage.initialize()
        
        # Run benchmark
        await run_benchmark(benchmark_config, storage, parallel_games)
        
        logger.info(f"Benchmark {benchmark_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Benchmark {benchmark_id} failed: {e}")
        raise
    finally:
        # Remove from running benchmarks
        if benchmark_id in running_benchmarks:
            del running_benchmarks[benchmark_id]


@router.post("/benchmarks/start", response_model=BenchmarkStartResponse)
async def start_benchmark(
    request: BenchmarkStartRequest,
    background_tasks: BackgroundTasks
):
    """Start a new benchmark run."""
    # Check if config file exists
    config_path = Path(request.config_path)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config file not found: {request.config_path}")
    
    # Generate or load benchmark ID
    try:
        with open(request.config_path) as f:
            config = json.load(f)
        
        if request.regenerate_id or not config.get("metadata", {}).get("benchmark_id"):
            benchmark_id = generate_benchmark_id()
        else:
            benchmark_id = config["metadata"]["benchmark_id"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load config: {e}")
    
    # Check if benchmark is already running
    if benchmark_id in running_benchmarks:
        return BenchmarkStartResponse(
            benchmark_id=benchmark_id,
            status="already_running",
            message=f"Benchmark {benchmark_id} is already running"
        )
    
    # Start benchmark in background
    task = asyncio.create_task(
        run_benchmark_task(
            request.config_path,
            request.results_dir,
            benchmark_id,
            request.parallel_games
        )
    )
    running_benchmarks[benchmark_id] = task
    
    return BenchmarkStartResponse(
        benchmark_id=benchmark_id,
        status="started",
        message=f"Benchmark {benchmark_id} started successfully"
    )


@router.get("/benchmarks/{benchmark_id}/status", response_model=BenchmarkStatus)
async def get_benchmark_status(benchmark_id: str, results_dir: str = "./results"):
    """Get current status of a benchmark."""
    storage: Storage = DirectoryStorage(results_dir, benchmark_id)
    await storage.initialize()
    
    config = await storage.get_config()
    results = await storage.get_benchmark_results()
    is_running = benchmark_id in running_benchmarks
    
    # Calculate progress if running
    progress = None
    if is_running and config and results:
        total_games = len(config.get("games", []))
        total_players = len(config.get("players", []))
        total_maps = config.get("metadata", {}).get("num_maps_per_game", 1)
        total_work_units = total_games * total_players * total_maps
        
        completed_results = len(results.get("game_results", []))
        progress = {
            "completed": completed_results,
            "total": total_work_units,
            "percentage": (completed_results / total_work_units * 100) if total_work_units > 0 else 0
        }
    
    return BenchmarkStatus(
        id=benchmark_id,
        exists=config is not None,
        is_running=is_running,
        progress=progress,
        config=config,
        results=results
    )


@router.get("/benchmarks")
async def list_benchmarks(results_dir: str = "./results"):
    """List all available benchmarks."""
    results_path = Path(results_dir)
    benchmarks = []
    
    if results_path.exists():
        for benchmark_dir in results_path.iterdir():
            if benchmark_dir.is_dir():
                benchmark_id = benchmark_dir.name
                is_running = benchmark_id in running_benchmarks
                
                # Try to get basic info
                storage: Storage = DirectoryStorage(results_dir, benchmark_id)
                await storage.initialize()
                config = await storage.get_config()
                
                benchmarks.append({
                    "id": benchmark_id,
                    "path": str(benchmark_dir),
                    "is_running": is_running,
                    "created": benchmark_dir.stat().st_ctime if benchmark_dir.exists() else None,
                    "has_config": config is not None
                })
    
    # Sort by creation time (newest first)
    benchmarks.sort(key=lambda x: x.get("created", 0), reverse=True)
    
    return {"benchmarks": benchmarks, "total": len(benchmarks)}


@router.post("/benchmarks/{benchmark_id}/stop")
async def stop_benchmark(benchmark_id: str):
    """Stop a running benchmark."""
    if benchmark_id not in running_benchmarks:
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} is not running")
    
    task = running_benchmarks[benchmark_id]
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    if benchmark_id in running_benchmarks:
        del running_benchmarks[benchmark_id]
    
    return {"message": f"Benchmark {benchmark_id} stopped", "status": "stopped"}