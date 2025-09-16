from xent.analysis.plot import (
    generate_normalized_score_summary_chart,
    generate_score_iteration_plots,
)
from xent.analysis.report import generate_markdown_report, generate_pdf
from xent.common.configuration_types import BenchmarkResult


def analyze(
    benchmark_result: BenchmarkResult, results_dir: str, make_pdf: bool = False
) -> None:
    generate_score_iteration_plots(benchmark_result, results_dir)
    generate_normalized_score_summary_chart(benchmark_result, results_dir)
    generate_markdown_report(benchmark_result, results_dir)
    if make_pdf:
        generate_pdf(results_dir, "report.md", "report.pdf")
