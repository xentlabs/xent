import pytest

from xega.common.errors import XegaSyntaxError
from xega.runtime.execution import eval_line, play_game

# REVEAL TESTS


@pytest.mark.asyncio
async def test_reveal_basic(xrt):
    """Test basic reveal operation to default player fails"""
    await eval_line("assign(s='test message')", 1, xrt)
    with pytest.raises(XegaSyntaxError):
        await eval_line("reveal(s)", 2, xrt)


@pytest.mark.asyncio
async def test_reveal_explicit_player(xrt):
    """Test reveal with explicit player specification."""
    await eval_line("assign(s='message for black')", 1, xrt)
    await eval_line("reveal(black, s)", 2, xrt)

    player = xrt.players[0]
    assert len(player.history) == 1
    assert "message for black" in player.history[0]


@pytest.mark.asyncio
async def test_reveal_multiple_values(xrt):
    """Test revealing multiple values at once."""
    await eval_line("assign(s1='first', s2='second', s3='third')", 1, xrt)
    await eval_line("reveal(black, s1, s2, s3)", 2, xrt)

    player = xrt.players[0]
    assert len(player.history) == 1
    # All values should be in the reveal
    assert "first" in player.history[0]
    assert "second" in player.history[0]
    assert "third" in player.history[0]


@pytest.mark.asyncio
async def test_reveal_to_different_players(xrt_multi_player):
    """Test revealing to different players."""
    xrt = xrt_multi_player
    await eval_line("assign(s='shared message')", 1, xrt)

    # Reveal to alice
    await eval_line("reveal(alice, s)", 2, xrt)
    alice = xrt.players[0]
    assert len(alice.history) == 1
    assert "shared message" in alice.history[0]

    # Bob should not have received it
    bob = xrt.players[1]
    assert len(bob.history) == 0

    # Now reveal to bob
    await eval_line("reveal(bob, s)", 3, xrt)
    assert len(bob.history) == 1
    assert "shared message" in bob.history[0]


@pytest.mark.asyncio
async def test_reveal_empty_string(xrt):
    """Test revealing empty strings."""
    await eval_line("assign(s='')", 1, xrt)
    await eval_line("reveal(black, s)", 2, xrt)

    player = xrt.players[0]
    assert len(player.history) == 1
    # The reveal should still happen even with empty string


@pytest.mark.asyncio
async def test_reveal_computed_values(xrt):
    """Test revealing computed values."""
    await eval_line("assign(s1='hello', s2='world')", 1, xrt)
    await eval_line("reveal(black, s1 + ' ' + s2)", 2, xrt)

    player = xrt.players[0]
    assert len(player.history) == 1
    assert "hello world" in player.history[0]


@pytest.mark.asyncio
async def test_reveal_only_positional_args(xrt):
    """Test that reveal only accepts positional arguments."""
    await eval_line("assign(s='test')", 1, xrt)

    # This should fail because reveal doesn't accept keyword arguments
    with pytest.raises(XegaSyntaxError):
        await eval_line("reveal(player=black, value=s)", 2, xrt)


# ELICIT TESTS


@pytest.mark.asyncio
async def test_elicit_basic(xrt):
    """Test basic elicit operation with default player."""
    await eval_line("elicit(s, 10)", 1, xrt)

    # Check that the variable was set
    assert "s" in xrt.local_vars
    assert str(xrt.local_vars["s"]) == "mocked_move"

    # Check that a previous_elicit beacon was created
    assert "previous_elicit" in xrt.beacons
    assert xrt.beacons["previous_elicit"].line_num == 1


@pytest.mark.asyncio
async def test_elicit_explicit_player(xrt):
    """Test elicit with explicit player specification."""
    await eval_line("elicit(black, s, 10)", 1, xrt)

    assert "s" in xrt.local_vars
    assert str(xrt.local_vars["s"]) == "mocked_move"


@pytest.mark.asyncio
async def test_elicit_multiple_variables(xrt):
    """Test eliciting multiple variables in one statement."""
    await eval_line("elicit(s1, s2, s3, 10)", 1, xrt)

    # All variables should be set
    assert "s1" in xrt.local_vars
    assert "s2" in xrt.local_vars
    assert "s3" in xrt.local_vars

    # Each should have received a move
    assert str(xrt.local_vars["s1"]) == "mocked_move"
    assert str(xrt.local_vars["s2"]) == "mocked_move"
    assert str(xrt.local_vars["s3"]) == "mocked_move"


@pytest.mark.asyncio
async def test_elicit_with_player_multiple_vars(xrt):
    """Test eliciting multiple variables with explicit player."""
    await eval_line("elicit(black, s1, s2, 10)", 1, xrt)

    assert "s1" in xrt.local_vars
    assert "s2" in xrt.local_vars
    assert str(xrt.local_vars["s1"]) == "mocked_move"
    assert str(xrt.local_vars["s2"]) == "mocked_move"


@pytest.mark.asyncio
async def test_elicit_token_limit(xrt):
    """Test elicit with different token limits."""
    # The token limit is passed as the last argument
    await eval_line("elicit(s1, 5)", 1, xrt)
    await eval_line("elicit(s2, 100)", 2, xrt)

    # Both should work (mock player doesn't respect token limit)
    assert "s1" in xrt.local_vars
    assert "s2" in xrt.local_vars


@pytest.mark.asyncio
async def test_elicit_missing_token_limit(xrt):
    """Test that elicit requires a token limit."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("elicit(s)", 1, xrt)

    with pytest.raises(XegaSyntaxError):
        await eval_line("elicit(black, s)", 1, xrt)


@pytest.mark.asyncio
async def test_elicit_only_positional_args(xrt):
    """Test that elicit only accepts positional arguments."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("elicit(var=s, limit=10)", 1, xrt)


@pytest.mark.asyncio
async def test_elicit_updates_last_elicit_player(xrt):
    """Test that elicit updates the last_elicit_player in runtime."""
    # Initially should be None
    assert xrt.last_elicit_player is None

    await eval_line("elicit(s, 10)", 1, xrt)

    # Should now point to the player
    assert xrt.last_elicit_player is not None
    assert xrt.last_elicit_player.name == "black"


@pytest.mark.asyncio
async def test_elicit_from_different_players(xrt_multi_player):
    """Test eliciting from different players in a multi-player game."""
    xrt = xrt_multi_player

    # Elicit from alice
    await eval_line("elicit(alice, s1, 10)", 1, xrt)
    assert xrt.last_elicit_player.name == "alice"

    # Elicit from bob
    await eval_line("elicit(bob, s2, 10)", 2, xrt)
    assert xrt.last_elicit_player.name == "bob"

    # Both variables should be set
    assert "s1" in xrt.local_vars
    assert "s2" in xrt.local_vars


# COMBINED TESTS


@pytest.mark.asyncio
async def test_reveal_elicit_interaction(xrt):
    """Test interaction between reveal and elicit."""
    game_code = """
    assign(s='Please enter a word')
    reveal(black, s)
    elicit(s1, 10)
    reveal(black, s1)
    """

    await play_game(game_code, xrt, auto_replay=False)

    player = xrt.players[0]
    # Should have received two reveals + elicit + elicit response
    assert len(player.history) == 4
    assert "Please enter a word" in player.history[0]
    assert "mocked_move" in player.history[3]


@pytest.mark.asyncio
async def test_multi_player_reveal_elicit(xrt_multi_player):
    """Test reveal and elicit in a multi-player context."""
    xrt = xrt_multi_player
    game_code = """
    assign(s='secret for alice')
    reveal(alice, s)
    elicit(alice, s1, 10)
    reveal(bob, s1)
    """

    await play_game(game_code, xrt, auto_replay=False)

    alice = xrt.players[0]
    bob = xrt.players[1]

    # Alice should have received the secret
    assert any("secret for alice" in h for h in alice.history)

    # Bob should have received alice's response
    assert any("mocked_move" in h for h in bob.history)

    # Bob should NOT have received the original secret
    assert not any("secret for alice" in h for h in bob.history)


@pytest.mark.asyncio
async def test_elicit_registers(xrt):
    """Test basic elicit operation with default player."""
    await eval_line("assign(s1='test1')", 1, xrt)
    await eval_line("assign(s2='test2')", 1, xrt)
    await eval_line("assign(s3='test3')", 1, xrt)
    await eval_line("assign(t1='test4')", 1, xrt)
    await eval_line("assign(t2='test5')", 1, xrt)
    await eval_line("assign(t3='test6')", 1, xrt)
    await eval_line("elicit(s, 10)", 1, xrt)

    player = xrt.players[0]
    assert player.event_history[-1]["type"] == "elicit_response"
    assert player.event_history[-2]["type"] == "elicit_request"
    event = player.event_history[-2]
    registers = event["registers"]
    assert len(registers) == 32  # 4 * 8 registers
    assert registers["s1"] == "test1"
    assert registers["s2"] == "test2"
    assert registers["s3"] == "test3"
    assert registers["t1"] == "test4"
    assert registers["t2"] == "test5"
    assert registers["t3"] == "test6"
