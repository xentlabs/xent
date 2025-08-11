import pytest

from xega.common.xega_types import XegaGameConfig
from xega.presentation.executor import get_default_presentation
from xega.runtime.default_players import MockXGP
from xega.runtime.execution import eval_line
from xega.runtime.judge import Judge
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals

FAKE_GAME_CONFIG: XegaGameConfig = {
    "game": {
        "name": "Token Usage Test",
        "code": "test_code",
        "map_seed": "test_seed_0",
        "presentation_function": get_default_presentation(),
    },
    "auto_replay": True,
    "max_steps": 100,
    "players": [
        {
            "name": "alice",
            "id": "test_alice",
            "player_type": "default",
            "options": {"model": "test", "provider": "test"},
        },
        {
            "name": "bob",
            "id": "test_bob",
            "player_type": "default",
            "options": {"model": "test", "provider": "test"},
        },
    ],
    "num_variables_per_register": 4,
    "num_maps_per_game": 1,
    "judge_model": "gpt2",
    "npc_players": [],
    "seed": "test_seed",
    "map_seed": "test_seed_0",
}


@pytest.mark.asyncio
async def test_token_accumulation_accuracy_single_player():
    """Test that multiple elicit calls correctly accumulate token usage for a single player."""
    game_config = FAKE_GAME_CONFIG.copy()
    # Create player with specific token usage per move
    player = MockXGP(
        "alice",
        "test_alice",
        {},
        game_config,
        token_usage_per_move={"input_tokens": 10, "output_tokens": 5},
    )
    locals = build_locals([player], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    xrt = XegaRuntime([player], locals, globals)

    # Make 3 elicit calls
    await eval_line("elicit(alice, s1, 20)", 1, xrt)
    await eval_line("elicit(alice, s2, 20)", 2, xrt)
    await eval_line("elicit(alice, s3, 20)", 3, xrt)

    # Check accumulated token usage
    assert xrt.token_usage["alice"]["input_tokens"] == 30  # 10 * 3
    assert xrt.token_usage["alice"]["output_tokens"] == 15  # 5 * 3


@pytest.mark.asyncio
async def test_token_accumulation_accuracy_multiple_players():
    """Test that token usage is tracked separately for multiple players."""
    game_config = FAKE_GAME_CONFIG.copy()
    # Create players with different token usage
    alice = MockXGP(
        "alice",
        "test_alice",
        {},
        game_config,
        token_usage_per_move={"input_tokens": 10, "output_tokens": 5},
    )
    bob = MockXGP(
        "bob",
        "test_bob",
        {},
        game_config,
        token_usage_per_move={"input_tokens": 20, "output_tokens": 8},
    )
    locals = build_locals([alice, bob], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    xrt = XegaRuntime([alice, bob], locals, globals)

    # Make elicit calls for both players
    await eval_line("elicit(alice, s1, 20)", 1, xrt)
    await eval_line("elicit(bob, s2, 20)", 2, xrt)
    await eval_line("elicit(alice, s3, 20)", 3, xrt)

    # Check that token usage is tracked separately
    assert xrt.token_usage["alice"]["input_tokens"] == 20  # 10 * 2
    assert xrt.token_usage["alice"]["output_tokens"] == 10  # 5 * 2
    assert xrt.token_usage["bob"]["input_tokens"] == 20  # 20 * 1
    assert xrt.token_usage["bob"]["output_tokens"] == 8  # 8 * 1


@pytest.mark.asyncio
async def test_game_iteration_reset():
    """Test that token usage resets between iterations but accumulates in final results."""
    game_config = FAKE_GAME_CONFIG.copy()
    player = MockXGP(
        "alice",
        "test_alice",
        {},
        game_config,
        token_usage_per_move={"input_tokens": 15, "output_tokens": 10},
    )
    locals = build_locals([player], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    xrt = XegaRuntime([player], locals, globals)

    # First iteration: make some moves
    await eval_line("elicit(alice, s1, 20)", 1, xrt)
    await eval_line("elicit(alice, s2, 20)", 2, xrt)

    # Check token usage after first iteration
    assert xrt.token_usage["alice"]["input_tokens"] == 30  # 15 * 2
    assert xrt.token_usage["alice"]["output_tokens"] == 20  # 10 * 2

    # Get results and reset (simulates end of game iteration)
    iteration1_result = xrt.get_results_and_reset()

    # Verify iteration result contains token usage
    assert iteration1_result["token_usage"]["alice"]["input_tokens"] == 30
    assert iteration1_result["token_usage"]["alice"]["output_tokens"] == 20

    # Verify runtime token usage was reset
    assert xrt.token_usage["alice"]["input_tokens"] == 0
    assert xrt.token_usage["alice"]["output_tokens"] == 0

    # Second iteration: make more moves
    await eval_line("elicit(alice, s3, 20)", 1, xrt)

    # Check token usage in second iteration
    assert xrt.token_usage["alice"]["input_tokens"] == 15  # 15 * 1
    assert xrt.token_usage["alice"]["output_tokens"] == 10  # 10 * 1

    # Get second iteration results
    iteration2_result = xrt.get_results_and_reset()
    assert iteration2_result["token_usage"]["alice"]["input_tokens"] == 15
    assert iteration2_result["token_usage"]["alice"]["output_tokens"] == 10

    # Simulate what extract_token_usage() function does
    from xega.benchmark.run_benchmark import extract_token_usage

    total_usage = extract_token_usage([iteration1_result, iteration2_result])

    # Verify total accumulation across iterations
    assert total_usage["alice"]["input_tokens"] == 45  # 30 + 15
    assert total_usage["alice"]["output_tokens"] == 30  # 20 + 10


@pytest.mark.asyncio
async def test_zero_token_usage():
    """Test handling of zero token usage scenarios."""
    game_config = FAKE_GAME_CONFIG.copy()
    player = MockXGP(
        "alice",
        "test_alice",
        {},
        game_config,
        token_usage_per_move={"input_tokens": 0, "output_tokens": 0},
    )
    locals = build_locals([player], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    xrt = XegaRuntime([player], locals, globals)

    # Make elicit call with zero token usage
    await eval_line("elicit(alice, s1, 20)", 1, xrt)

    # Verify zero accumulation works correctly
    assert xrt.token_usage["alice"]["input_tokens"] == 0
    assert xrt.token_usage["alice"]["output_tokens"] == 0

    # Test reset with zero values
    result = xrt.get_results_and_reset()
    assert result["token_usage"]["alice"]["input_tokens"] == 0
    assert result["token_usage"]["alice"]["output_tokens"] == 0
