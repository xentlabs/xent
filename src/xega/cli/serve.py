"""CLI command to serve the web interface."""

import click
import uvicorn


@click.command()
@click.option(
    "--port",
    default=8000,
    help="Port to run the web server on",
    type=int,
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the server to",
)
@click.option(
    "--reload",
    "--dev",
    is_flag=True,
    help="Enable auto-reload for development",
)
@click.option(
    "--log-level",
    default="info",
    help="Logging level (debug, info, warning, error, critical)",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
)
def serve(port: int, host: str, reload: bool, log_level: str):
    """Start web interface for benchmark monitoring.
    
    This command starts a local web server that provides a browser-based
    interface for running and monitoring XEGA benchmarks.
    
    Examples:
        # Start server on default port (8000)
        xega serve
        
        # Start server on custom port with development mode
        xega serve --port 3000 --dev
        
        # Start server accessible from network
        xega serve --host 0.0.0.0
    """
    click.echo(f"Starting XEGA web interface on http://{host}:{port}")
    
    if reload:
        click.echo("Running in development mode with auto-reload enabled")
    
    # Run the FastAPI server
    uvicorn.run(
        "xega.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )