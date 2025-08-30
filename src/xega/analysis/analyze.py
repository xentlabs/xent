import json
import os

from xega.analysis.plot import (
    generate_normalized_score_summary_chart,
    generate_score_iteration_plots,
)
from xega.analysis.report import generate_markdown_report, generate_pdf
from xega.common.configuration_types import BenchmarkResult


def extract_results_from_dir(results_dir: str) -> BenchmarkResult:
    benchmark_files = [
        f
        for f in os.listdir(results_dir)
        if f.startswith("benchmark_")
        and f.endswith(".json")
        and f != "benchmark_config.json"
    ]

    if not benchmark_files:
        raise FileNotFoundError("No benchmark result file found")

    benchmark_file = benchmark_files[0]  # Take the first one if multiple exist

    with open(os.path.join(results_dir, benchmark_file)) as f:
        benchmark_result: BenchmarkResult = json.load(f)

    return benchmark_result


def analyze(
    benchmark_result: BenchmarkResult, results_dir: str, make_pdf: bool = False
) -> None:
    generate_score_iteration_plots(benchmark_result, results_dir)
    generate_normalized_score_summary_chart(benchmark_result, results_dir)
    generate_markdown_report(benchmark_result, results_dir)
    if make_pdf:
        generate_pdf(results_dir, "report.md", "report.pdf")
