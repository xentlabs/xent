"""FastAPI server for XEGA web interface."""

import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from xega.web.api import router as api_router
from xega.web.websocket import benchmark_monitor

logger = logging.getLogger(__name__)

app = FastAPI(title="XEGA Benchmark Monitor", version="0.1.0")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "XEGA Web Interface",
        "version": "0.1.0"
    }

# Serve static files in production
static_path = Path(__file__).parent / "static"
if static_path.exists():
    # Mount static assets
    assets_path = static_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="static")
    
    # Serve index.html for the root and all non-API routes (SPA routing)
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_spa(path: str = ""):
        from fastapi import HTTPException
        # Don't serve index.html for API or WebSocket routes
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend not built. Run 'npm run build' in the web directory.")


@app.websocket("/ws/benchmarks/{benchmark_id}")
async def websocket_endpoint(websocket: WebSocket, benchmark_id: str):
    """WebSocket endpoint for real-time benchmark updates."""
    await benchmark_monitor(websocket, benchmark_id)