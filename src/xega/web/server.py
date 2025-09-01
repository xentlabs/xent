import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from xega.benchmark.expand_benchmark import expand_benchmark_config
from xega.benchmark.run_benchmark import run_benchmark
from xega.common.configuration_types import CondensedXegaBenchmarkConfig
from xega.storage.directory_storage import DirectoryBenchmarkStorage, DirectoryStorage

app = FastAPI(title="XEGA Web Interface")

STORAGE_DIR = Path.cwd() / "results"
storage = DirectoryStorage(STORAGE_DIR)


class ConfigRequest(BaseModel):
    config: CondensedXegaBenchmarkConfig


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
        # Get the config to verify benchmark exists
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
