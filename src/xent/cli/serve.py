"""CLI command to serve the web interface."""

import threading
import time
import webbrowser

import click
import uvicorn


@click.command()
@click.option("--port", default=8000, help="Port to run the web server on", type=int)
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def serve(port: int, host: str, no_browser: bool):
    """Start web interface for benchmark monitoring."""
    url = f"http://{host}:{port}"
    click.echo(f"Starting XENT web interface on {url}")

    if not no_browser:

        def open_browser():
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("xent.web.server:app", host=host, port=port)
