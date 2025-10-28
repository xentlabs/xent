import asyncio
import datetime
import logging
import os
from pathlib import Path

import pytest
from typeguard import check_type

from xent.analysis.analyze import analyze
from xent.analysis.plot import (
    generate_normalized_score_summary_chart,
    generate_score_iteration_plots,
)
from xent.analysis.report import generate_markdown_report
from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.benchmark.run_benchmark import run_benchmark
from xent.cli.configure import DEFAULT_EXPANSION_CONFIG
from xent.cli.run import DEFAULT_XENT_METADATA
from xent.common.configuration_types import (
    CondensedXentBenchmarkConfig,
    ExecutableGameMap,
    ExpandedXentBenchmarkConfig,
    ExpansionConfig,
    GameConfig,
    PlayerConfig,
    XentMetadata,
)
from xent.common.util import dumps
from xent.presentation.executor import get_default_presentation
from xent.runtime.execution import play_game
from xent.runtime.players.default_players import MockXGP
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_locals
from xent.storage.directory_storage import DirectoryBenchmarkStorage


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


def create_test_benchmark_config() -> CondensedXentBenchmarkConfig:
    """Create a comprehensive benchmark config for testing all scenarios"""
    id_string = (
        datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        + "-"
        + hex(hash(str(datetime.datetime.now().timestamp())))[-6:]
    )
    return CondensedXentBenchmarkConfig(
        config_type="condensed_xent_config",
        metadata=XentMetadata(
            benchmark_id=id_string,
            xent_version=DEFAULT_XENT_METADATA["xent_version"],
            num_rounds_per_game=1,
            judge_model=DEFAULT_XENT_METADATA["judge_model"],
            seed=DEFAULT_XENT_METADATA["seed"],
            store_full_player_interactions=False,
            npcs=[],
        ),
        expansion_config=ExpansionConfig(
            num_maps_per_game=DEFAULT_EXPANSION_CONFIG["num_maps_per_game"],
            text_generation_config={
                "generator_type": "JUDGE",
                "generator_config": {},
                "max_length": 50,
            },
        ),
        games=[
            # Game 1: Simple single player test
            GameConfig(
                name="test_single",
                code="""
                    assign(s1="At the book club, I ran into this girl, Neila, who claims to only read books backwards: starting from the bottom-right corner of the last page and reading all the words in reverse order until the beginning, finishing with the title. Doesn't it spoil the fun of the story? Apparently not, she told me. The suspense is just distributed somewhat differently (some books' beginnings are apparently all too predictable), and some books get better or worse if you read them in one direction or another. She started reading backwards at age seven. Her name was sort of a predisposition.", s2="Hello, it is today a lovely day to use my skills in differential geometry and in the calculus of variation to estimate how much grass I will be able to eat. I aim to produce a lot of milk and to write a lot of theorems for my children, because that's what the beauty of life is about, dear physicists and cheese-makers. Have a great day!")
                    reveal(s1, s2)
                    elicit(x, 20)
                    reward(xent(x | s1))
                    reward(-xent(s2 | (s1+x)))
                """,
                presentation_function=get_default_presentation(),
            ),
            # Game 2: Multi-step test
            GameConfig(
                name="test_multi",
                code="""
                    assign(t1="At the book club, I ran into this girl, Neila, who claims to only read books backwards: starting from the bottom-right corner of the last page and reading all the words in reverse order until the beginning, finishing with the title. Doesn't it spoil the fun of the story? Apparently not, she told me. The suspense is just distributed somewhat differently (some books' beginnings are apparently all too predictable), and some books get better or worse if you read them in one direction or another. She started reading backwards at age seven. Her name was sort of a predisposition.", t2="Hello, it is today a lovely day to use my skills in differential geometry and in the calculus of variation to estimate how much grass I will be able to eat. I aim to produce a lot of milk and to write a lot of theorems for my children, because that's what the beauty of life is about, dear physicists and cheese-makers. Have a great day!")
                    reveal(t1)
                    elicit(y, 15)
                    reward(xent(y | t1))
                    reveal(t2)
                    reward(-xent(t2 | y))
                """,
                presentation_function=get_default_presentation(),
            ),
            GameConfig(
                name="test_lists",
                code="""
                    assign(l=["a bunch of", "different words", "for testing purposes", "that are", "unlikey to shuffle", "in the same", "order"])
                    reveal(l)
                    elicit(s, 10)
                    assign(t=sample(l))
                    assign(l2=shuffle(l))
                    reveal(l2)
                    reveal(t)
                    reward(xent(t | s))
                """,
                presentation_function=get_default_presentation(),
            ),
        ],
        players=[
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
    )


@pytest.fixture(scope="module")
def shared_benchmark_results(module_test_data_dir):
    """Run benchmark once and share results across all tests"""

    benchmark_config = create_test_benchmark_config()
    logging.info(f"Running shared benchmark with config: {benchmark_config}")
    print(dumps(benchmark_config, indent=4))

    expanded_config = expand_benchmark_config(benchmark_config)
    check_type(expanded_config, ExpandedXentBenchmarkConfig)
    # Run the benchmark once in the event loop
    storage = DirectoryBenchmarkStorage(
        Path(module_test_data_dir), benchmark_config["metadata"]["benchmark_id"]
    )
    asyncio.run(storage.initialize())
    asyncio.run(storage.store_config(expanded_config))
    benchmark_results = asyncio.run(run_benchmark(expanded_config, storage, 1))

    # Also run the full analysis pipeline once
    analyze(benchmark_results, f"{module_test_data_dir}", make_pdf=False)

    return {
        "config": expanded_config,
        "results": benchmark_results,
        "test_dir": module_test_data_dir,
    }


@pytest.mark.integration
def test_benchmark_structure(shared_benchmark_results):
    """Test benchmark execution and result structure"""
    benchmark_config = shared_benchmark_results["config"]
    benchmark_results = shared_benchmark_results["results"]

    # Verify config wasn't mutated
    assert benchmark_results["expanded_config"] == benchmark_config

    # Verify version is present in the expanded config and results
    assert isinstance(benchmark_config["metadata"]["xent_version"], str)
    assert len(benchmark_config["metadata"]["xent_version"]) > 0
    assert "xent_version" in benchmark_results["expanded_config"]["metadata"]
    assert (
        benchmark_results["expanded_config"]["metadata"]["xent_version"]
        == benchmark_config["metadata"]["xent_version"]
    )

    # Verify we have results for all games
    game_results = benchmark_results["results"]
    assert len(game_results) == 3

    # Test Game 1 (simple single player)
    game1_result = game_results[0]
    assert len(game1_result["round_results"]) == 1  # Single round

    game1_iteration = game1_result["round_results"][0]
    assert game1_result["score"] == game1_iteration["score"]
    event_types = [e["type"] for e in game1_iteration["history"]]
    expected_types = [
        "round_started",
        "reveal",
        "elicit_request",
        "elicit_response",
        "reward",
        "reward",
        "reward",
        "reward",
        "round_finished",
    ]
    assert event_types == expected_types

    # Test Game 2 (multi-step)
    game2_result = game_results[1]
    assert len(game2_result["round_results"]) == 1  # Single round

    game2_iteration = game2_result["round_results"][0]
    event_types = [e["type"] for e in game2_iteration["history"]]
    expected_types = [
        "round_started",
        "reveal",
        "elicit_request",
        "elicit_response",
        "reward",
        "reward",
        "reveal",
        "reward",
        "reward",
        "round_finished",
    ]
    assert event_types == expected_types

    # Test Game 3 (test-lists)
    game3_result = game_results[2]
    assert len(game3_result["round_results"]) == 1  # Single round

    game3_iteration = game3_result["round_results"][0]
    event_types = [e["type"] for e in game3_iteration["history"]]
    expected_types = [
        "round_started",
        "reveal",
        "elicit_request",
        "elicit_response",
        "reveal",
        "reveal",
        "reward",
        "reward",
        "round_finished",
    ]
    assert event_types == expected_types

    reveal_events = [
        event for event in game3_iteration["history"] if event["type"] == "reveal"
    ]
    assert len(reveal_events) == 3

    original_list = reveal_events[0]["values"]["l"]
    assert isinstance(original_list, list)
    assert original_list == [
        "a bunch of",
        "different words",
        "for testing purposes",
        "that are",
        "unlikey to shuffle",
        "in the same",
        "order",
    ]

    shuffled_list = reveal_events[1]["values"]["l2"]

    assert isinstance(shuffled_list, list)
    assert shuffled_list != original_list
    assert sorted(shuffled_list) == sorted(original_list)

    sampled_value = reveal_events[2]["values"]["t"]
    assert isinstance(sampled_value, str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_interaction_flag_records_extra_data():
    """Full interaction flag records prompts and responses in history."""

    presentation_code = """
from xent.presentation.sdk import ChatBuilder

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    b = ChatBuilder()
    b.user('prompt')
    return b.render()
"""

    async def run_case(store_flag: bool):
        executable_game_map: ExecutableGameMap = {
            "game_map": {
                "name": "simple",
                "code": "elicit(x, 5)",
                "map_seed": "seed",
                "presentation_function": presentation_code,
            },
            "metadata": {
                "benchmark_id": "bench",
                "xent_version": "0.0.0",
                "num_rounds_per_game": 1,
                "judge_model": "test",
                "seed": "seed",
                "store_full_player_interactions": store_flag,
                "npcs": [],
            },
            "player": {
                "name": "black",
                "id": "mock",
                "player_type": "mock",
                "options": {},
            },
        }

        player = MockXGP("black", "mock", {}, executable_game_map)
        locals_dict = build_locals(player, [], executable_game_map)
        globals_dict = {
            "__builtins__": {"len": len},
            "first_n_tokens": lambda text, n: str(text)[:n],
        }

        xrt = XentRuntime(
            player,
            [],
            locals_dict,
            globals_dict,
            store_full_interactions=store_flag,
        )

        results = await play_game(
            executable_game_map["game_map"]["code"], xrt, num_rounds=1
        )
        history = results[0]["history"]
        return next(event for event in history if event["type"] == "elicit_response")

    enriched_event = await run_case(True)
    baseline_event = await run_case(False)

    assert isinstance(enriched_event.get("prompts"), list)
    assert enriched_event.get("full_response", "") == "full mocked_move"
    assert "prompts" not in baseline_event
    assert "full_response" not in baseline_event


@pytest.mark.integration
def test_all_outputs_generated(shared_benchmark_results):
    """Test that all expected outputs are generated correctly"""
    test_dir = shared_benchmark_results["test_dir"]
    benchmark_config = shared_benchmark_results["config"]
    benchmark_id = benchmark_config["metadata"]["benchmark_id"]

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
    with open(report_path) as f:
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
        assert f"{game['name']}_score_vs_iteration.png" in report_content

    # Check model information
    player_id = str(benchmark_config["players"][0]["id"])
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
    config = CondensedXentBenchmarkConfig(
        config_type="condensed_xent_config",
        metadata=XentMetadata(
            benchmark_id=id_string,
            xent_version=DEFAULT_XENT_METADATA["xent_version"],
            num_rounds_per_game=2,  # Very low for speed
            judge_model=DEFAULT_XENT_METADATA["judge_model"],
            seed=DEFAULT_XENT_METADATA["seed"],
            npcs=[],
        ),
        expansion_config=ExpansionConfig(
            num_maps_per_game=DEFAULT_EXPANSION_CONFIG["num_maps_per_game"],
            text_generation_config={
                "generator_type": "JUDGE",
                "generator_config": {},
                "max_length": 50,
            },
        ),
        games=[
            GameConfig(
                name="smoke",
                code="assign(s=story())\nreveal(s)\nelicit(x, 5)\nreward(xent(x | s))",
                presentation_function=get_default_presentation(),
            ),
        ],
        players=[
            PlayerConfig(
                name="black",
                id="qwen3:0.6b",
                player_type="default",
                options={"provider": "ollama", "model": "qwen3:0.6b"},
            ),
        ],
    )

    expanded_config = expand_benchmark_config(config)
    check_type(expanded_config, ExpandedXentBenchmarkConfig)

    storage = DirectoryBenchmarkStorage(
        Path(test_data_dir), expanded_config["metadata"]["benchmark_id"]
    )
    await storage.initialize()
    await storage.store_config(expanded_config)
    results = await run_benchmark(expanded_config, storage, 1)
    assert results["expanded_config"]["metadata"]["benchmark_id"] == id_string
    assert len(results["results"]) == 1
