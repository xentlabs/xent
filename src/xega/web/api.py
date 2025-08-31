"""API endpoints for XEGA web interface."""

import logging
from pathlib import Path

from fastapi import APIRouter

from xega.storage.directory_storage import DirectoryStorage
from xega.storage.storage_interface import Storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/benchmarks/{benchmark_id}/status")
async def get_benchmark_status(benchmark_id: str, results_dir: str = "./results"):
    """Get current status of a benchmark."""
    storage: Storage = DirectoryStorage(results_dir, benchmark_id)
    await storage.initialize()
    
    config = await storage.get_config()
    results = await storage.get_benchmark_results()
    
    # Calculate progress if data exists
    progress = None
    if config and results:
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
    
    return {
        "id": benchmark_id,
        "exists": config is not None,
        "progress": progress,
        "config": config,
        "results": results
    }


@router.get("/benchmarks")
async def list_benchmarks(results_dir: str = "./results"):
    """List all available benchmarks."""
    results_path = Path(results_dir)
    benchmarks = []
    
    if results_path.exists():
        for benchmark_dir in results_path.iterdir():
            if benchmark_dir.is_dir():
                benchmark_id = benchmark_dir.name
                
                # Try to get basic info
                storage: Storage = DirectoryStorage(results_dir, benchmark_id)
                await storage.initialize()
                config = await storage.get_config()
                
                benchmarks.append({
                    "id": benchmark_id,
                    "path": str(benchmark_dir),
                    "created": benchmark_dir.stat().st_ctime if benchmark_dir.exists() else None,
                    "has_config": config is not None
                })
    
    # Sort by creation time (newest first)
    benchmarks.sort(key=lambda x: x.get("created", 0), reverse=True)
    
    return {"benchmarks": benchmarks, "total": len(benchmarks)}