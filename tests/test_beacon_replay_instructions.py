import logging

import pytest

from xega.common.errors import XegaGameError, XegaInternalError, XegaSyntaxError
from xega.common.x_flag import XFlag
from xega.runtime.execution import eval_line, play_game

# BEACON TESTS


@pytest.mark.asyncio
async def test_beacon_basic(xrt):
    """Test basic beacon creation."""
    await eval_line("beacon(flag_1)", 5, xrt)

    # Should create a beacon
    assert "flag_1" in xrt.beacons
    flag = xrt.beacons["flag_1"]
    assert isinstance(flag, XFlag)
    assert flag.name == "flag_1"
    assert flag.line_num == 5


@pytest.mark.asyncio
async def test_beacon_flag_2(xrt):
    """Test beacon with flag_2."""
    await eval_line("beacon(flag_2)", 10, xrt)

    assert "flag_2" in xrt.beacons
    flag = xrt.beacons["flag_2"]
    assert flag.name == "flag_2"
    assert flag.line_num == 10


@pytest.mark.asyncio
async def test_beacon_overwrite(xrt):
    """Test that setting beacon twice overwrites the first one."""
    await eval_line("beacon(flag_1)", 5, xrt)
    assert xrt.beacons["flag_1"].line_num == 5

    await eval_line("beacon(flag_1)", 10, xrt)
    assert xrt.beacons["flag_1"].line_num == 10


@pytest.mark.asyncio
async def test_beacon_only_one_arg(xrt):
    """Test that beacon only accepts a single argument."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("beacon(flag_1, flag_2)", 1, xrt)


@pytest.mark.asyncio
async def test_beacon_only_positional_arg(xrt):
    """Test that beacon only accepts positional arguments."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("beacon(flag=flag_1)", 1, xrt)


@pytest.mark.asyncio
async def test_beacon_invalid_flag(xrt):
    """Test beacon with invalid flag name."""
    # Only flag_1 and flag_2 are valid
    with pytest.raises(XegaGameError):
        await eval_line("beacon(flag_3)", 1, xrt)

    with pytest.raises(XegaGameError):
        await eval_line("beacon(invalid_flag)", 1, xrt)


# REPLAY TESTS


@pytest.mark.asyncio
async def test_replay_basic(xrt):
    """Test basic replay functionality."""
    # Set a beacon first
    await eval_line("beacon(flag_1)", 2, xrt)

    # Replay should jump to the beacon
    result = await eval_line("replay(flag_1, 1)", 5, xrt)
    assert isinstance(result, XFlag)
    assert result.line_num == 2


@pytest.mark.asyncio
async def test_replay_counter(xrt):
    """Test replay counter functionality."""
    game_code = """
    assign(s="1")
    beacon(flag_1)
    assign(s=s+"1")
    replay(flag_1, 3)
    assign(t='done')
    """

    await play_game(game_code, xrt, auto_replay=False)

    # Initial length + 1 for first run + 3 for replays
    assert len(xrt.local_vars["s"]) == 5
    assert str(xrt.local_vars["t"]) == "done"


@pytest.mark.asyncio
async def test_replay_without_beacon(xrt):
    """Test replay without setting beacon first."""
    with pytest.raises(XegaInternalError):
        await eval_line("replay(flag_1, 1)", 1, xrt)


@pytest.mark.asyncio
async def test_replay_zero_count(xrt):
    """Test replay with zero count."""
    await eval_line("beacon(flag_1)", 1, xrt)

    # Zero count should not jump
    result = await eval_line("replay(flag_1, 0)", 2, xrt)
    assert result is None  # Should continue to next line


@pytest.mark.asyncio
async def test_replay_tracks_per_line(xrt):
    """Test that replay counters are tracked per line."""
    game_code = """
    beacon(flag_1)
    reveal(black, 'loop')
    replay(flag_1, 2)
    beacon(flag_2)
    reveal(black, 'inner')
    replay(flag_1, 1)
    """

    await play_game(game_code, xrt, auto_replay=False, max_steps=20)

    # Check history to see execution pattern
    player = xrt.players[0]
    # Should see multiple 'loop' and 'inner' reveals
    logging.info(
        f"&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&Player history: {player.history}"
    )
    loop_count = sum(1 for h in player.history if "loop" in h)
    inner_count = sum(1 for h in player.history if "inner" in h)

    assert loop_count > 0
    assert inner_count > 0


@pytest.mark.asyncio
async def test_replay_with_two_flags(xrt):
    """Test using both flag_1 and flag_2."""
    game_code = """
    beacon(flag_1)
    assign(s='first')
    beacon(flag_2)
    assign(s='second')
    replay(flag_2, 1)
    replay(flag_1, 1)
    """

    await play_game(game_code, xrt, auto_replay=False, max_steps=10)

    # Should have executed both replays
    assert len(xrt.replay_counters) >= 2


# COMBINED BEACON/REPLAY TESTS


@pytest.mark.asyncio
async def test_auto_replay_at_end(xrt):
    """Test that auto_replay creates an implicit replay at the end."""
    game_code = """
    assign(s='hello')
    reveal(black, s)
    reward(xent('hello world'))
    """

    game_results = await play_game(game_code, xrt, auto_replay=True, max_steps=10)

    # Should have multiple game results from auto replay
    assert len(game_results) > 1

    # Each iteration should give the same reward
    for result in game_results:
        assert result["scores"]["black"] > 0


@pytest.mark.asyncio
async def test_main_flag(xrt):
    """Test explicit replay of main beacon."""
    game_code = """
    assign(s='test')
    reveal(black, s)
    replay(main, 3)
    """

    await play_game(game_code, xrt, auto_replay=False)

    player = xrt.players[0]
    # Should have executed the replay 3 times, but it doesn't create a new history entry
    assert len(player.history) == 1


@pytest.mark.asyncio
async def test_main_flag_no_reveal(xrt):
    """Test explicit replay of main beacon."""
    game_code = """
    assign(s='test')
    elicit(black, t, 10)
    replay(main, 3)
    """

    await play_game(game_code, xrt, auto_replay=False)

    player = xrt.players[0]
    logging.info(f"Player history: {player.history}")
    assert len(player.history) == 8  # 4x elicit request + response
