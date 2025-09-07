"""CLI command to serve the web interface."""

import click
import uvicorn


@click.command()
@click.option("--port", default=8000, help="Port to run the web server on", type=int)
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
def serve(port: int, host: str):
    """Start web interface for benchmark monitoring."""
    click.echo(f"Starting XEGA web interface on http://{host}:{port}")
    uvicorn.run("xega.web.server:app", host=host, port=port)
