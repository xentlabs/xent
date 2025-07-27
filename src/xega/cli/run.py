import asyncio
import json
import logging
import os

import click

from xega.analysis import analyze
from xega.benchmark.expand_benchmark import expand_benchmark_config
from xega.benchmark.run_benchmark import run_benchmark
from xega.cli.cli_util import generate_benchmark_id
from xega.common.xega_types import (
    ExpandedXegaBenchmarkConfig,
    XegaBenchmarkConfig,
    XegaMetadata,
)

DEFAULT_XEGA_CONFIG = XegaMetadata(
    judge_model="gpt2",
    auto_replay=True,
    max_steps=100,
    seed="notrandom",
    num_variables_per_register=4,
    npc_players=[],
    num_maps_per_game=1,
)


def load_benchmark_config(
    benchmark_config_file_path: str,
) -> XegaBenchmarkConfig | ExpandedXegaBenchmarkConfig:
    with open(benchmark_config_file_path) as f:
        benchmark_config = json.load(f)

    return benchmark_config


@click.command()
@click.option(
    "--config",
    default="./xega_config.json",
    help="Path to json configuration for Xega benchmark",
)
@click.option(
    "--results-dir",
    help="Path to directory where results dir will be created",
    default="./results",
)
@click.option(
    "--dont-analyze",
    is_flag=True,
    help="If set, no reporting or charting will be generated from the results after running",
)
@click.option(
    "--clean",
    is_flag=True,
    help="If set, the results directory will be cleaned before running the benchmark. This will delete all existing results. Be careful! If you specify this option, it will delete all files in the results/<benchmark_id> directory.",
)
@click.option(
    "--regenerate-id",
    is_flag=True,
    help="If set, a new benchmark ID will be generated. This is useful for running the same benchmark multiple times without overwriting previous results.",
)
@click.option(
    "--parallel-games",
    default=1,
    help="Number of games to run in parallel. Default is 1. Increase this for higher throughput benchmarking.",
)
@click.option(
    "-v", "--verbose", count=True, help="Enable verbose logging (-v, -vv, -vvv)"
)
def run(
    config: str,
    results_dir: str,
    dont_analyze: bool,
    clean: bool,
    regenerate_id: bool,
    verbose: int,
    parallel_games: int,
):
    """Execute Xega benchmark"""
    log_level = logging.WARNING
    logging_format = (
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    if verbose == 1:
        log_level = logging.INFO
    elif verbose >= 2:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format=logging_format)

    benchmark_config = load_benchmark_config(config)
    if regenerate_id:
        benchmark_id = generate_benchmark_id()
        logging.info(f"Generated new benchmark ID: {benchmark_id}")
        benchmark_config["benchmark_id"] = benchmark_id

    if benchmark_config["config_type"] != "expanded_benchmark_config":
        benchmark_config = expand_benchmark_config(benchmark_config)

    results_dir = os.path.join(results_dir, benchmark_config["benchmark_id"])
    if clean:
        if os.path.exists(results_dir):
            logging.info(f"Cleaning results directory: {results_dir}")
            for root, dirs, files in os.walk(results_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))

    os.makedirs(results_dir, exist_ok=True)

    logger = logging.getLogger()
    file_handler = logging.FileHandler(os.path.join(results_dir, "log.txt"))
    file_handler.setLevel(log_level)
    formatter = logging.Formatter(logging_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    benchmark_result = asyncio.run(
        run_benchmark(benchmark_config, results_dir, parallel_games)
    )
    if not dont_analyze:
        logging.info("Performing analysis on benchmark results")
        analyze.analyze(benchmark_result, results_dir)
