import asyncio
import logging
import os
from pathlib import Path

import click

from xent.analysis.analyze import analyze as analyze_results
from xent.storage.directory_storage import DirectoryBenchmarkStorage


@click.command()
@click.option(
    "--benchmark-id",
    required=True,
    help="Benchmark Id to analyze",
)
@click.option(
    "--storage-dir",
    required=True,
    help="Storage directory. This should contain a sub-directory with the benchmark data. Used for loading benchmark results as well as output directory for analysis results",
)
@click.option(
    "--generate-pdf",
    is_flag=True,
    help="Also generate a PDF report from the markdown",
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def analyze(
    benchmark_id: str, storage_dir: str, generate_pdf: bool, verbose: bool, debug: bool
) -> None:
    """Analyze completed benchmark results"""
    log_level = logging.WARNING
    logging_format = (
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    if verbose:
        log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format=logging_format)
    storage = DirectoryBenchmarkStorage(Path(storage_dir), benchmark_id)
    asyncio.run(storage.initialize())
    results = asyncio.run(storage.get_benchmark_results())
    if results is None:
        print("No benchmark results found at target path")
        return
    results_dir = os.path.join(storage_dir, benchmark_id)
    analyze_results(results, results_dir, make_pdf=generate_pdf)
