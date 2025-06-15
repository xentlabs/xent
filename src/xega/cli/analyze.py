import logging

import click

from xega.analysis.analyze import analyze as analyze_results
from xega.analysis.analyze import extract_results_from_dir


@click.command()
@click.option(
    "--results-dir",
    required=True,
    help="Results directory. Used for loading benchmark results as well as output directory for analysis results",
)
@click.option(
    "--generate-pdf",
    is_flag=True,
    help="Also generate a PDF report from the markdown",
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def analyze(results_dir: str, generate_pdf: bool, verbose: bool, debug: bool) -> None:
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
    results = extract_results_from_dir(results_dir)
    analyze_results(results, results_dir, make_pdf=generate_pdf)
