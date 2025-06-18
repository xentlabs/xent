import pytest

from xega.runtime.execution import eval_line, play_game


@pytest.mark.asyncio
async def test_reward_basic_number(xrt):
    """Test basic reward with a numeric value."""
    player = xrt.players[0]
    initial_score = player.get_score()

    await eval_line("reward(xent('hello world'))", 1, xrt)

    final_score = player.get_score()
    assert final_score > initial_score


@pytest.mark.asyncio
async def test_reward_negative_number(xrt):
    """Test reward with negative value."""
    player = xrt.players[0]
    initial_score = player.get_score()

    await eval_line("reward(-xent('hello world'))", 1, xrt)

    final_score = player.get_score()
    assert final_score < initial_score


@pytest.mark.asyncio
async def test_reward_explicit_player(xrt):
    """Test reward with explicit player specification."""
    player = xrt.players[0]
    assert player.name == "black"
    initial_score = player.get_score()

    await eval_line("reward(black, xent('hello world'))", 1, xrt)

    final_score = player.get_score()
    assert final_score > initial_score


@pytest.mark.asyncio
async def test_reward_xent_value(xrt):
    """Test reward with cross-entropy value."""
    player = xrt.players[0]
    initial_score = player.get_score()

    await eval_line("reward(xent('hello world this is a test'))", 1, xrt)

    final_score = player.get_score()
    # xent should return a positive value
    assert final_score > initial_score


@pytest.mark.asyncio
async def test_reward_xent_expression(xrt):
    """Test reward with cross-entropy expression."""
    player = xrt.players[0]
    initial_score = player.get_score()

    await eval_line(
        "reward(xent('hello world') - xent('hello world' | 'first thing that prints for a program'))",
        1,
        xrt,
    )

    final_score = player.get_score()
    # The difference should be positive (longer string has higher xent)
    assert final_score > initial_score


@pytest.mark.asyncio
async def test_reward_zero_sum_players(xrt_zero_sum):
    """Test that reward to zero-sum players affects both."""
    xrt = xrt_zero_sum
    black = xrt.players[0]
    white = xrt.players[1]

    black_initial = black.get_score()
    white_initial = white.get_score()

    # Reward black
    await eval_line("reward(black, xent('hello world'))", 1, xrt)

    # Black should gain, white should lose
    assert black.get_score() > black_initial
    assert white.get_score() < white_initial

    # Reward white
    await eval_line(
        "reward(white, xent('hello world this is a longer string and xent will be more'))",
        2,
        xrt,
    )

    # White should gain, black should lose
    assert white.get_score() > white_initial
    assert black.get_score() < black_initial


@pytest.mark.asyncio
async def test_reward_non_zero_sum_players(xrt_multi_player):
    """Test that reward to non-zero-sum players only affects the target."""
    xrt = xrt_multi_player
    alice = xrt.players[0]
    bob = xrt.players[1]

    alice_initial = alice.get_score()
    bob_initial = bob.get_score()

    # Reward alice
    await eval_line("reward(alice, xent('hello world'))", 1, xrt)

    # Only alice should be affected
    alice_temp = alice.get_score()
    assert alice_temp > alice_initial
    assert bob.get_score() == bob_initial

    # Reward bob
    await eval_line("reward(bob, xent('hello world'))", 2, xrt)

    # Only bob should be affected
    assert bob.get_score() > bob_initial
    assert alice.get_score() == alice_temp


@pytest.mark.asyncio
async def test_reward_only_positional_args(xrt):
    """Test that reward only accepts positional arguments."""
    with pytest.raises(Exception):
        await eval_line("reward(player=black, amount=10)", 1, xrt)


@pytest.mark.asyncio
async def test_reward_xed_function(xrt):
    """Test reward with xed function."""
    await eval_line("assign(s='hello world')", 1, xrt)
    player = xrt.players[0]
    initial_score = player.get_score()

    # xed(s1 | s2) = xent(s1) - xent(s1 | s2)
    await eval_line("reward(xed(s | 'first program prints'))", 2, xrt)

    final_score = player.get_score()
    # xed should be positive (prefix helps predict the suffix)
    assert final_score > initial_score


@pytest.mark.asyncio
async def test_reward_in_game_context(xrt):
    """Test reward in a complete game context."""
    game_code = """
    assign(s='My favorite breakfast is huevos rancheros')
    reveal(black, s)
    elicit(s1, 20)
    reward(black, xed(s | s1))
    """
    start_score = xrt.local_vars["black"].get_score()

    game_results = await play_game(game_code, xrt, auto_replay=False)
    assert len(game_results) == 1

    # Player should have received some reward
    assert game_results[0]["scores"]["black"] != start_score


@pytest.mark.asyncio
async def test_reward_history(xrt):
    """Test that reward operations are logged in history."""
    await eval_line("reward(xent('hello world'))", 1, xrt)

    assert len(xrt.history) > 0
    assert xrt.history[-1]["type"] == "reward"
