"""WebSocket handlers for real-time updates."""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

from xega.storage.directory_storage import DirectoryStorage
from xega.storage.storage_interface import Storage

logger = logging.getLogger(__name__)

# Track active connections per benchmark
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for benchmark monitoring."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, benchmark_id: str):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        if benchmark_id not in self.active_connections:
            self.active_connections[benchmark_id] = set()
        self.active_connections[benchmark_id].add(websocket)
        logger.info(f"WebSocket connected for benchmark {benchmark_id}")
    
    def disconnect(self, websocket: WebSocket, benchmark_id: str):
        """Remove a WebSocket connection."""
        if benchmark_id in self.active_connections:
            self.active_connections[benchmark_id].discard(websocket)
            if not self.active_connections[benchmark_id]:
                del self.active_connections[benchmark_id]
        logger.info(f"WebSocket disconnected for benchmark {benchmark_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def broadcast(self, message: dict, benchmark_id: str):
        """Broadcast a message to all connections for a benchmark."""
        if benchmark_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[benchmark_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to connection: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[benchmark_id].discard(conn)


# Global connection manager
manager = ConnectionManager()


async def benchmark_monitor(websocket: WebSocket, benchmark_id: str, results_dir: str = "./results"):
    """Monitor a benchmark and send real-time updates via WebSocket."""
    await manager.connect(websocket, benchmark_id)
    
    storage: Storage = DirectoryStorage(results_dir, benchmark_id)
    await storage.initialize()
    
    try:
        last_results = None
        last_config = None
        error_count = 0
        max_errors = 5
        
        while True:
            try:
                # Poll storage for updates
                current_config = await storage.get_config()
                current_results = await storage.get_benchmark_results()
                
                # Send initial state or updates
                if current_config != last_config:
                    await websocket.send_json({
                        "type": "config_update",
                        "benchmark_id": benchmark_id,
                        "data": current_config
                    })
                    last_config = current_config
                
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
                
                # Reset error count on successful iteration
                error_count = 0
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in benchmark monitor loop: {e}")
                
                if error_count >= max_errors:
                    logger.error(f"Too many errors, closing connection for benchmark {benchmark_id}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Too many errors occurred",
                        "benchmark_id": benchmark_id
                    })
                    break
            
            # Wait before next poll
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from benchmark {benchmark_id}")
    except Exception as e:
        logger.error(f"WebSocket error for benchmark {benchmark_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "benchmark_id": benchmark_id
            })
        except:
            pass
    finally:
        manager.disconnect(websocket, benchmark_id)