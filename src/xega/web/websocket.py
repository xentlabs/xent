"""WebSocket handler for real-time updates."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from xega.storage.directory_storage import DirectoryStorage
from xega.storage.storage_interface import Storage

logger = logging.getLogger(__name__)


async def benchmark_monitor(websocket: WebSocket, benchmark_id: str, results_dir: str = "./results"):
    """Monitor a benchmark and send real-time updates via WebSocket."""
    await websocket.accept()
    logger.info(f"WebSocket connection established for benchmark {benchmark_id}")
    
    storage: Storage = DirectoryStorage(results_dir, benchmark_id)
    await storage.initialize()
    
    try:
        last_results = None
        last_config = None
        
        while True:
            try:
                # Poll storage for updates
                current_config = await storage.get_config()
                current_results = await storage.get_benchmark_results()
                
                # Send config if changed
                if current_config != last_config:
                    await websocket.send_json({
                        "type": "config_update",
                        "benchmark_id": benchmark_id,
                        "data": current_config
                    })
                    last_config = current_config
                
                # Send results if changed
                if current_results != last_results:
                    # Calculate progress
                    progress = None
                    if current_config and current_results:
                        total_games = len(current_config.get("games", []))
                        total_players = len(current_config.get("players", []))
                        total_maps = current_config.get("metadata", {}).get("num_maps_per_game", 1)
                        total_work_units = total_games * total_players * total_maps
                        
                        completed_results = len(current_results.get("game_results", []))
                        progress = {
                            "completed": completed_results,
                            "total": total_work_units,
                            "percentage": (completed_results / total_work_units * 100) if total_work_units > 0 else 0
                        }
                    
                    await websocket.send_json({
                        "type": "results_update",
                        "benchmark_id": benchmark_id,
                        "progress": progress,
                        "data": current_results
                    })
                    last_results = current_results
                
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "benchmark_id": benchmark_id
                })
                
            except Exception as e:
                logger.error(f"Error in benchmark monitor loop: {e}")
                break
            
            # Wait before next poll
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from benchmark {benchmark_id}")
    except Exception as e:
        logger.error(f"WebSocket error for benchmark {benchmark_id}: {e}")
    finally:
        logger.info(f"WebSocket connection closed for benchmark {benchmark_id}")