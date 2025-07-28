# pyright: reportUnusedExpression=false
import pytest

from xega.common.errors import XegaConfigurationError, XegaGameError, XegaSyntaxError
from xega.runtime.execution import eval_line, play_game

# SYNTAX AND PARSING ERRORS


@pytest.mark.asyncio
async def test_unknown_instruction(xrt):
    """Test that unknown instructions raise exceptions."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("unknown_instruction(x='test')", 1, xrt)

    with pytest.raises(XegaSyntaxError):
        await eval_line("this_does_not_exist()", 1, xrt)


@pytest.mark.asyncio
async def test_malformed_syntax(xrt):
    """Test various malformed syntax errors."""
    # Missing closing parenthesis
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign(s='test'", 1, xrt)

    # Missing quotes
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=test)", 1, xrt)

    # Invalid Python syntax
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign s='test'", 1, xrt)


@pytest.mark.asyncio
async def test_empty_instruction(xrt):
    """Test empty instruction lines."""
    # Empty string should be OK (no-op)
    result = await eval_line("", 1, xrt)
    assert result is None

    # Just whitespace should also be OK
    result = await eval_line("   ", 1, xrt)
    assert result is None

    # Comment lines should be OK
    result = await eval_line("# This is a comment", 1, xrt)
    assert result is None


# ARGUMENT ERRORS


@pytest.mark.asyncio
async def test_wrong_argument_types(xrt):
    """Test instructions with wrong argument types."""
    # assign with positional args
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign('s', 'value')", 1, xrt)

    # reveal with keyword args
    with pytest.raises(XegaSyntaxError):
        await eval_line("reveal(player=black, value='test')", 1, xrt)

    # ensure with keyword args
    with pytest.raises(XegaSyntaxError):
        await eval_line("ensure(condition=True)", 1, xrt)


@pytest.mark.asyncio
async def test_missing_required_args(xrt):
    """Test instructions with missing required arguments."""
    # elicit without token limit
    with pytest.raises(XegaSyntaxError):
        await eval_line("elicit(s)", 1, xrt)

    # beacon without flag
    with pytest.raises(XegaSyntaxError):
        await eval_line("beacon()", 1, xrt)

    # replay without arguments
    with pytest.raises(XegaSyntaxError):
        await eval_line("replay()", 1, xrt)


@pytest.mark.asyncio
async def test_too_many_args(xrt):
    """Test instructions with too many arguments."""
    # beacon with multiple flags
    with pytest.raises(XegaSyntaxError):
        await eval_line("beacon(flag_1, flag_2)", 1, xrt)


# REGISTER ERRORS


@pytest.mark.asyncio
async def test_invalid_register_names(xrt):
    """Test operations with invalid register names."""
    # Invalid register type
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign(z='invalid')", 1, xrt)

    # Register number too high
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign(s99='too_high')", 1, xrt)

    # Invalid format
    with pytest.raises(XegaSyntaxError):
        await eval_line("assign(1s='invalid')", 1, xrt)


@pytest.mark.asyncio
async def test_undefined_register_access(xrt):
    """Test accessing undefined registers."""
    # Accessing undefined register in expression
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=undefined_var)", 1, xrt)

    # Using undefined register in reveal
    with pytest.raises(XegaGameError):
        await eval_line("reveal(black, undefined_var)", 1, xrt)


# PLAYER ERRORS


@pytest.mark.asyncio
async def test_invalid_player_names(xrt):
    """Test operations with invalid player names."""
    # Invalid player in reveal
    with pytest.raises(XegaGameError):
        await eval_line("reveal(invalid_player, 'test')", 1, xrt)

    # Invalid player in elicit
    with pytest.raises(XegaGameError):
        await eval_line("elicit(invalid_player, s, 10)", 1, xrt)

    # Invalid player in reward
    with pytest.raises(XegaGameError):
        await eval_line("reward(invalid_player, 10)", 1, xrt)


# FUNCTION ERRORS


@pytest.mark.asyncio
async def test_undefined_functions(xrt):
    """Test calling undefined functions."""
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=undefined_function())", 1, xrt)

    with pytest.raises(XegaGameError):
        await eval_line("assign(s=random_func('arg'))", 1, xrt)


@pytest.mark.asyncio
async def test_wrong_function_args(xrt):
    """Test functions with wrong number of arguments."""
    # xent with no args
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=xent())", 1, xrt)

    # get_story with args (should take none)
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=get_story('arg'))", 1, xrt)

    # first_n_tokens with wrong number of args
    with pytest.raises(XegaGameError):
        await eval_line("assign(s=first_n_tokens('string'))", 1, xrt)


# GAME LIMIT ERRORS


@pytest.mark.asyncio
async def test_code_too_long(xrt):
    """Test that code over 64 lines is rejected."""
    # Create code with more than 64 lines
    long_code = "\n".join([f"assign(s{i}='test')" for i in range(65)])

    with pytest.raises(XegaConfigurationError) as exc_info:
        await play_game(long_code, xrt)

    assert "64 lines" in str(exc_info.value)


@pytest.mark.asyncio
async def test_max_steps_exceeded(xrt):
    """Test that games stop after max_steps."""
    # Infinite loop game
    game_code = """
    beacon(flag_1)
    assign(s='loop')
    replay(flag_1, 1000)
    """

    _ = await play_game(game_code, xrt, auto_replay=False, max_steps=10)

    # Should have stopped after max_steps
    # Check that we didn't actually do 1000 iterations
    assert len(xrt.history) <= 10


# TYPE ERRORS


@pytest.mark.asyncio
async def test_type_mismatches(xrt):
    """Test various type mismatches."""
    # Numeric operations on strings
    await eval_line("assign(s='hello')", 1, xrt)
    with pytest.raises(XegaGameError):
        await eval_line("assign(t=s + 5)", 2, xrt)

    # String operations on numbers
    with pytest.raises(XegaGameError):
        await eval_line("ensure(len(5) > 0)", 1, xrt)


# EDGE CASES


@pytest.mark.asyncio
async def test_special_characters_in_strings(xrt):
    """Test strings with special characters that might break parsing."""
    # Strings with parentheses
    await eval_line("assign(s='test(with)parens')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "test(with)parens"

    # Strings with commas
    await eval_line("assign(s='test,with,commas')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "test,with,commas"

    # Strings that look like code
    await eval_line("assign(s='assign(x=\"nested\")')", 1, xrt)
    assert "assign" in str(xrt.local_vars["s"])
