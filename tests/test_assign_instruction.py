import pytest

from xega.common.x_string import XString
from xega.runtime.execution import eval_line, play_game


@pytest.mark.asyncio
async def test_assign_basic_string(xrt):
    """Test basic string assignment to registers."""
    # Test assignment to different register types
    await eval_line("assign(s='hello')", 1, xrt)
    assert isinstance(xrt.local_vars["s"], XString)
    assert str(xrt.local_vars["s"]) == "hello"

    await eval_line("assign(t='world')", 1, xrt)
    assert str(xrt.local_vars["t"]) == "world"

    await eval_line("assign(x='test')", 1, xrt)
    assert str(xrt.local_vars["x"]) == "test"


@pytest.mark.asyncio
async def test_assign_multiple_variables(xrt):
    """Test assigning multiple variables in one statement."""
    await eval_line("assign(s='hello', t='world', x='test')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "hello"
    assert str(xrt.local_vars["t"]) == "world"
    assert str(xrt.local_vars["x"]) == "test"


@pytest.mark.asyncio
async def test_assign_numbered_registers(xrt):
    """Test assignment to numbered registers (e.g., s1, s2, etc.)."""
    await eval_line("assign(s1='first', s2='second', s3='third')", 1, xrt)
    assert str(xrt.local_vars["s1"]) == "first"
    assert str(xrt.local_vars["s2"]) == "second"
    assert str(xrt.local_vars["s3"]) == "third"


@pytest.mark.asyncio
async def test_assign_static_registers(xrt):
    """Test that assignment to static registers is not allowed."""
    # Static register types are: ["a", "b", "c"]
    with pytest.raises(Exception):
        await eval_line("assign(a='should_fail')", 1, xrt)

    with pytest.raises(Exception):
        await eval_line("assign(b1='should_fail')", 1, xrt)

    with pytest.raises(Exception):
        await eval_line("assign(c='should_fail')", 1, xrt)


@pytest.mark.asyncio
async def test_assign_function_results(xrt):
    """Test assigning results of functions to registers."""
    await eval_line("assign(t=story())", 1, xrt)
    assert "t" in xrt.local_vars
    assert len(str(xrt.local_vars["t"])) > 0


@pytest.mark.asyncio
async def test_assign_string_operations(xrt):
    """Test assigning results of string operations."""
    # Setup some strings first
    await eval_line("assign(s1='hello world', s2='world')", 1, xrt)

    # Test concatenation
    await eval_line("assign(s3=s1 + ' test')", 1, xrt)
    assert str(xrt.local_vars["s3"]) == "hello world test"

    # Test // operation (substring before)
    await eval_line("assign(s3=s1 // s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == "hello "

    # Test % operation (substring after)
    await eval_line("assign(s3=s1 % s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == ""  # Since "world" is at the end

    # Test with a different example
    await eval_line("assign(s1='hello world again', s2='world')", 1, xrt)
    await eval_line("assign(s3=s1 % s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == " again"


@pytest.mark.asyncio
async def test_assign_empty_string(xrt):
    """Test assigning empty strings."""
    await eval_line("assign(s='')", 1, xrt)
    assert str(xrt.local_vars["s"]) == ""

    # Test operations with empty strings
    await eval_line("assign(s1='hello', s2='')", 1, xrt)
    await eval_line("assign(s3=s1 // s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == "hello"  # s1 // "" should return s1

    await eval_line("assign(s3=s1 % s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == ""  # s1 % "" should return ""


@pytest.mark.asyncio
async def test_assign_complex_expressions(xrt):
    """Test assigning results of complex expressions."""
    # Test function chaining
    await eval_line("assign(s1=story(), s2=first_n_tokens(s1, 5))", 1, xrt)
    assert "s2" in xrt.local_vars

    # Test nested operations dont work
    # First, lets clear the state
    await eval_line("assign(s1='', s2='', s3='')", 1, xrt)
    await eval_line("assign(s1='hello', s1='world', s3=(s1 + ' ') + s2)", 1, xrt)
    assert str(xrt.local_vars["s3"]) == " "


@pytest.mark.asyncio
async def test_assign_overwrite(xrt):
    """Test that assignments overwrite previous values."""
    await eval_line("assign(s='first')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "first"

    await eval_line("assign(s='second')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "second"


@pytest.mark.asyncio
async def test_assign_with_positional_args(xrt):
    """Test that assign only accepts keyword arguments."""
    with pytest.raises(Exception):
        await eval_line("assign('should_fail')", 1, xrt)

    with pytest.raises(Exception):
        await eval_line("assign('s', 'value')", 1, xrt)


@pytest.mark.asyncio
async def test_assign_invalid_register_names(xrt):
    """Test assignment to invalid register names."""
    # Test invalid register type
    with pytest.raises(Exception):
        await eval_line("assign(z='invalid')", 1, xrt)

    # Test register number out of bounds (assuming num_registers_per_type is 4)
    with pytest.raises(Exception):
        await eval_line("assign(s10='too_high')", 1, xrt)


@pytest.mark.asyncio
async def test_assign_special_characters(xrt):
    """Test assignment of strings with special characters."""
    await eval_line("assign(s='hello\\nworld')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "hello\nworld"

    await eval_line("assign(s='tab\\there')", 1, xrt)
    assert str(xrt.local_vars["s"]) == "tab\there"

    await eval_line('assign(s="quotes \' and \\"")', 1, xrt)
    assert "quotes" in str(xrt.local_vars["s"])


@pytest.mark.asyncio
async def test_assign_in_game_context(xrt):
    """Test assign instruction within a full game context."""
    game_code = """
    assign(s1='hello', s2='world')
    assign(s3=s1 + ' ' + s2)
    reveal(black, s3)
    """

    game_results = await play_game(game_code, xrt, auto_replay=False)
    assert len(game_results) == 1

    # Check that the assignments worked by looking at the reveal
    player_history = xrt.players[0].history
    assert any("hello world" in str(h) for h in player_history)
