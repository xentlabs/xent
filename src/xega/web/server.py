from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from xega.benchmark.expand_benchmark import expand_benchmark_config
from xega.common.configuration_types import CondensedXegaBenchmarkConfig
from xega.storage.directory_storage import DirectoryStorage

app = FastAPI(title="XEGA Web Interface")

STORAGE_DIR = Path.cwd() / "results"


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
        storage = DirectoryStorage(STORAGE_DIR)
        configs = await storage.list_configs()
        return [config["metadata"]["benchmark_id"] for config in configs]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list benchmarks: {str(e)}"
        ) from e


@app.post("/api/config")
async def store_config(request: ConfigRequest):
    try:
        expanded_config = expand_benchmark_config(request.config)
        storage = DirectoryStorage(STORAGE_DIR)
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
