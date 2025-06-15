import datetime
import logging
import os

import pytest

from xega.analysis.analyze import analyze, extract_results_from_dir
from xega.analysis.plot import (
    generate_normalized_score_summary_chart,
    generate_score_iteration_plots,
)
from xega.analysis.report import generate_markdown_report
from xega.benchmark.run_benchmark import run_benchmark
from xega.cli.run import DEFAULT_XEGA_CONFIG
from xega.common.util import dumps
from xega.common.xega_types import GameConfig, PlayerConfig, XegaBenchmarkConfig


@pytest.fixture
def test_data_dir(tmp_path):
    test_dir = tmp_path / "benchmark_results"
    test_dir.mkdir()
    yield test_dir


@pytest.fixture(scope="module")
def module_test_data_dir(tmp_path_factory):
    """Module-scoped temporary directory for shared benchmark results"""
    test_dir = tmp_path_factory.mktemp("benchmark_results")
    yield test_dir


def create_test_benchmark_config() -> XegaBenchmarkConfig:
    """Create a comprehensive benchmark config for testing all scenarios"""
    id_string = (
        datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        + "-"
        + hex(hash(str(datetime.datetime.now().timestamp())))[-6:]
    )
    return XegaBenchmarkConfig(
        benchmark_id=id_string,
        games=[
            # Game 1: Simple single player test
            GameConfig(
                name="test_single",
                code="""
                    assign(s1=story(), s2=story())
                    reveal(black, s1, s2)
                    elicit(black, x, 20)
                    reward(xent(x | s1))
                    reward(-xent(s2 | (s1+x)))
                """,
            ),
            # Game 2: Multi-step test
            GameConfig(
                name="test_multi",
                code="""
                    assign(t1=story(), t2=story())
                    reveal(black, t1)
                    elicit(black, y, 15)
                    reward(xent(y | t1))
                    reveal(black, t2)
                    reward(-xent(t2 | y))
                """,
            ),
        ],
        players=[
            # Single player configuration
            [
                PlayerConfig(
                    name="black",
                    id="qwen3:0.6b",
                    player_type="default",
                    options={
                        "provider": "ollama",
                        "model": "qwen3:0.6b",
                    },
                ),
            ],
        ],
        auto_replay=False,
        max_steps=100,
        judge_model=DEFAULT_XEGA_CONFIG["judge_model"],
        npc_players=DEFAULT_XEGA_CONFIG["npc_players"],
        num_variables_per_register=DEFAULT_XEGA_CONFIG["num_variables_per_register"],
        seed=DEFAULT_XEGA_CONFIG["seed"],
        num_maps_per_game=DEFAULT_XEGA_CONFIG["num_maps_per_game"],
    )


@pytest.fixture(scope="module")
def shared_benchmark_results(module_test_data_dir):
    """Run benchmark once and share results across all tests"""
    import asyncio

    benchmark_config = create_test_benchmark_config()
    logging.info(f"Running shared benchmark with config: {benchmark_config}")
    print(dumps(benchmark_config, indent=4))

    # Run the benchmark once in the event loop
    benchmark_results = asyncio.run(
        run_benchmark(benchmark_config, f"{module_test_data_dir}")
    )

    # Also run the full analysis pipeline once
    analyze(benchmark_results, f"{module_test_data_dir}", make_pdf=False)

    return {
        "config": benchmark_config,
        "results": benchmark_results,
        "test_dir": module_test_data_dir,
    }


@pytest.mark.integration
def test_benchmark_structure(shared_benchmark_results):
    """Test benchmark execution and result structure"""
    benchmark_config = shared_benchmark_results["config"]
    benchmark_results = shared_benchmark_results["results"]

    # Verify config wasn't mutated
    assert benchmark_results["config"] == benchmark_config

    # Verify we have results for both games
    game_results = benchmark_results["game_results"]
    assert len(game_results) == 2

    # Test Game 1 (simple single player)
    game1_result = game_results[0]
    assert len(game1_result["scores"].keys()) == 1
    assert len(game1_result["game_results"]) == 1  # No auto replay

    game1_iteration = game1_result["game_results"][0]
    assert len(game1_iteration["scores"].keys()) == 1
    assert game1_result["scores"]["black"] == game1_iteration["scores"]["black"]
    assert (
        len(game1_iteration["xrt_history"]) == 5
    )  # reveal, elicit(req), elicit(resp), reward, reward

    # Test Game 2 (multi-step)
    game2_result = game_results[1]
    assert len(game2_result["scores"].keys()) == 1
    assert len(game2_result["game_results"]) == 1  # No auto replay

    game2_iteration = game2_result["game_results"][0]
    assert len(game2_iteration["xrt_history"]) > 5  # More steps than game 1


@pytest.mark.integration
def test_analyze_extraction(shared_benchmark_results):
    """Test that analyze.extract_results_from_dir works correctly"""
    test_dir = shared_benchmark_results["test_dir"]
    benchmark_config = shared_benchmark_results["config"]
    benchmark_results = shared_benchmark_results["results"]

    # Extract results from directory
    extracted_results = extract_results_from_dir(f"{test_dir}")

    # Verify extraction
    assert (
        extracted_results["config"]["benchmark_id"] == benchmark_config["benchmark_id"]
    )
    assert len(extracted_results["game_results"]) == len(
        benchmark_results["game_results"]
    )
    assert extracted_results["config"] == benchmark_results["config"]


@pytest.mark.integration
def test_all_outputs_generated(shared_benchmark_results):
    """Test that all expected outputs are generated correctly"""
    test_dir = shared_benchmark_results["test_dir"]
    benchmark_config = shared_benchmark_results["config"]
    benchmark_id = benchmark_config["benchmark_id"]

    # Check individual game plots
    for game in benchmark_config["games"]:
        plot_path = os.path.join(test_dir, f"{game['name']}_score_vs_iteration.png")
        assert os.path.exists(plot_path), f"Plot for {game['name']} not created"
        assert os.path.getsize(plot_path) > 0, f"Plot for {game['name']} is empty"

    # Check summary chart
    summary_path = os.path.join(
        test_dir, f"benchmark_{benchmark_id}_normalized_score_summary.png"
    )
    assert os.path.exists(summary_path), "Summary chart not created"
    assert os.path.getsize(summary_path) > 0, "Summary chart is empty"

    # Check markdown report
    report_path = os.path.join(test_dir, "report.md")
    assert os.path.exists(report_path), "Markdown report not created"

    # Verify report content
    with open(report_path, "r") as f:
        report_content = f.read()

    # Check report structure
    assert "# AI Game Experiment Results" in report_content
    assert f"**Benchmark ID:** {benchmark_id}" in report_content
    assert "## Score Summary" in report_content
    assert "## Detailed Game Results" in report_content

    # Check both games are included
    for game in benchmark_config["games"]:
        assert f"### Game: {game['name']}" in report_content
        assert "#### Game Code" in report_content
        assert "#### Game Configuration" in report_content
        assert "##### Average Player Scores" in report_content
        assert game["code"] in report_content
        assert f"{game['name']}_score_vs_iteration.png" in report_content

    # Check model information
    player_id = str(benchmark_config["players"][0][0]["id"])
    assert player_id in report_content

    # Check summary chart reference
    assert f"benchmark_{benchmark_id}_normalized_score_summary.png" in report_content


@pytest.mark.integration
def test_individual_analysis_functions(shared_benchmark_results):
    """Test individual analysis functions work correctly"""
    test_dir = shared_benchmark_results["test_dir"]
    benchmark_results = shared_benchmark_results["results"]

    # Since analyze() was already run in the fixture, we'll test that
    # running individual functions doesn't break anything

    # Test regenerating plots (should overwrite existing)
    generate_score_iteration_plots(benchmark_results, f"{test_dir}")
    generate_normalized_score_summary_chart(benchmark_results, f"{test_dir}")
    generate_markdown_report(benchmark_results, f"{test_dir}")

    # Files should still exist and be valid
    test_all_outputs_generated(shared_benchmark_results)


# Optional: Add a quick smoke test that doesn't use the shared fixture
@pytest.mark.integration
@pytest.mark.asyncio
async def test_minimal_benchmark_smoke(test_data_dir):
    """Quick smoke test with minimal configuration"""
    id_string = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    config = XegaBenchmarkConfig(
        benchmark_id=id_string,
        games=[
            GameConfig(
                name="smoke",
                code="assign(s=story())\nreveal(black, s)\nelicit(black, x, 5)\nreward(xent(x | s))",
            ),
        ],
        players=[
            [
                PlayerConfig(
                    name="black",
                    id="qwen3:0.6b",
                    player_type="default",
                    options={"provider": "ollama", "model": "qwen3:0.6b"},
                ),
            ]
        ],
        auto_replay=False,
        max_steps=10,  # Very low for speed
        judge_model=DEFAULT_XEGA_CONFIG["judge_model"],
        npc_players=DEFAULT_XEGA_CONFIG["npc_players"],
        num_variables_per_register=DEFAULT_XEGA_CONFIG["num_variables_per_register"],
        seed=DEFAULT_XEGA_CONFIG["seed"],
        num_maps_per_game=DEFAULT_XEGA_CONFIG["num_maps_per_game"],
    )

    results = await run_benchmark(config, f"{test_data_dir}")
    assert results["config"]["benchmark_id"] == id_string
    assert len(results["game_results"]) == 1
