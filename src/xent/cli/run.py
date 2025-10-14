import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click

from xent.analysis import analyze
from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.benchmark.run_benchmark import run_benchmark
from xent.cli.cli_util import generate_benchmark_id
from xent.common.configuration_types import (
    CondensedXentBenchmarkConfig,
    ExpandedXentBenchmarkConfig,
    ExpansionConfig,
    XentMetadata,
)
from xent.common.util import dumps, log_git_snapshot
from xent.common.version import get_xent_version, validate_version
from xent.storage.directory_storage import DirectoryBenchmarkStorage
from xent.storage.storage_interface import BenchmarkStorage

DEFAULT_XENT_METADATA = XentMetadata(
    benchmark_id="",
    xent_version=get_xent_version(),
    judge_model="gpt2",
    num_rounds_per_game=30,
    seed="notrandom",
    store_full_player_interactions=False,
    npcs=[],
)

DEFAULT_EXPANSION_CONFIG = ExpansionConfig(
    num_maps_per_game=1,
    text_generation_config={
        "generator_type": "JUDGE",
        "generator_config": {},
        "max_length": 50,
    },
)


def load_benchmark_config(
    benchmark_config_file_path: str,
) -> CondensedXentBenchmarkConfig | ExpandedXentBenchmarkConfig:
    with open(benchmark_config_file_path) as f:
        benchmark_config = json.load(f)

    return benchmark_config


@click.command()
@click.option(
    "--config",
    default="./xent_config.json",
    help="Path to json configuration for Xent benchmark",
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
    "--ignore-version-mismatch",
    is_flag=True,
    help="If set, ignore version mismatches between configuration and runtime. Use with caution as results may not be comparable.",
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
    ignore_version_mismatch: bool,
):
    """Execute Xent benchmark"""
    logging_format = (
        "%(asctime)s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s"
    )
    formatter = logging.Formatter(logging_format)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    if verbose == 1:
        console_handler.setLevel(logging.INFO)
    elif verbose >= 2:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.WARNING)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    benchmark_config = load_benchmark_config(config)
    if regenerate_id:
        benchmark_id = generate_benchmark_id()
        logging.info(f"Generated new benchmark ID: {benchmark_id}")
        benchmark_config["metadata"]["benchmark_id"] = benchmark_id

    if benchmark_config["config_type"] != "expanded_xent_config":
        benchmark_config = expand_benchmark_config(benchmark_config)

    check_version(benchmark_config, ignore_version_mismatch)

    scoped_results_dir = os.path.join(
        results_dir, benchmark_config["metadata"]["benchmark_id"]
    )

    storage: BenchmarkStorage = DirectoryBenchmarkStorage(
        Path(results_dir), benchmark_config["metadata"]["benchmark_id"]
    )

    asyncio.run(storage.initialize())
    if clean:
        asyncio.run(storage.clear())

    # TODO how to handle this with non-directory storage?
    log_file_path = os.path.join(scoped_results_dir, "log.txt")
    file_handler = logging.FileHandler(log_file_path)

    # File handler should always log INFO, or DEBUG if verbosity is high
    if verbose >= 2:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    log_git_snapshot()

    benchmark_result = asyncio.run(
        run_benchmark(benchmark_config, storage, parallel_games)
    )

    with open(os.path.join(scoped_results_dir, "benchmark_results.json"), "w") as f:
        f.write(dumps(benchmark_result, indent=4))

    if not dont_analyze:
        logging.info("Performing analysis on benchmark results")
        analyze.analyze(benchmark_result, scoped_results_dir)


def check_version(
    benchmark_config: ExpandedXentBenchmarkConfig, ignore_version_mismatch: bool
):
    config_version = benchmark_config["metadata"]["xent_version"]
    current_version = get_xent_version()
    print(f"Config: {config_version}")
    print(f"Current: {current_version}")
    is_valid, message = validate_version(config_version, current_version)

    if not is_valid and not ignore_version_mismatch:
        logging.error(message)
        logging.error(
            "Use --ignore-version-mismatch to bypass this check (not recommended)"
        )
        sys.exit(1)
    elif not is_valid and ignore_version_mismatch:
        logging.warning(message)
        logging.warning(
            "Proceeding despite version mismatch (--ignore-version-mismatch specified)"
        )
    elif config_version is None:
        # Old config without version field
        logging.warning(message)
    else:
        logging.debug(message)
