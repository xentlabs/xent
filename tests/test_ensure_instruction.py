import pytest

from xega.common.errors import XegaSyntaxError
from xega.common.x_flag import XFlag
from xega.runtime.execution import eval_line, play_game
from xega.runtime.runtime import MAX_ENSURE_FAILURES


@pytest.mark.asyncio
async def test_ensure_before_elicit(xrt):
    """Test ensure before elicit throws"""
    with pytest.raises(XegaSyntaxError):
        await eval_line("ensure(1 == 1)", 1, xrt)


@pytest.mark.asyncio
async def test_ensure_true_condition(xrt):
    """Test ensure with a condition that evaluates to True."""
    # This should pass without issue
    await eval_line("elicit(s, 10)", 1, xrt)
    result = await eval_line("ensure(1 == 1)", 2, xrt)
    assert result is None  # Should continue to next line


@pytest.mark.asyncio
async def test_ensure_false_condition(xrt):
    """Test ensure with a condition that evaluates to False."""
    # First need an elicit to jump back to
    await eval_line("elicit(s, 10)", 1, xrt)

    # This should fail and jump back
    result = await eval_line("ensure(1 == 2)", 2, xrt)
    assert isinstance(result, XFlag)
    assert result.line_num == 1  # Should jump back to the elicit


@pytest.mark.asyncio
async def test_ensure_multiple_conditions_all_true(xrt):
    """Test ensure with multiple conditions that all evaluate to True."""
    await eval_line("elicit(s, 10)", 1, xrt)
    await eval_line("assign(s='hello')", 2, xrt)
    result = await eval_line("ensure(1 == 1, 2 == 2, len(s) == 5)", 3, xrt)
    assert result is None  # Should continue


@pytest.mark.asyncio
async def test_ensure_multiple_conditions_one_false(xrt):
    """Test ensure with multiple conditions where one is False."""
    await eval_line("elicit(s, 10)", 1, xrt)
    await eval_line("assign(x='test')", 2, xrt)

    # One false condition should cause failure
    result = await eval_line("ensure(1 == 1, 2 == 3, len(x) == 4)", 3, xrt)
    assert isinstance(result, XFlag)
    assert result.line_num == 1


@pytest.mark.asyncio
async def test_ensure_with_xent_comparisons(xrt):
    """Test ensure with cross-entropy comparisons."""
    await eval_line("elicit(s, 10)", 1, xrt)
    # Test equality of xent values
    result = await eval_line("ensure(xent('hello') == xent('hello'))", 2, xrt)
    assert result is None

    # Test inequality
    result = await eval_line(
        "ensure(xent('hello world') == xent('asdfasdf adsfasdf'))", 3, xrt
    )
    assert isinstance(result, XFlag)


@pytest.mark.asyncio
async def test_ensure_with_string_operations(xrt):
    """Test ensure with string operation conditions."""
    await eval_line("assign(s='hello world')", 1, xrt)
    await eval_line("elicit(x, 10)", 2, xrt)

    # Test various string conditions
    result = await eval_line("ensure('world' in s, len(s) > 5)", 3, xrt)
    assert result is None

    # Test failed condition
    result = await eval_line("ensure('xyz' in s)", 4, xrt)
    assert isinstance(result, XFlag)
    assert result.line_num == 2


@pytest.mark.asyncio
async def test_ensure_only_positional_args(xrt):
    """Test that ensure only accepts positional arguments."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("ensure(condition=True)", 1, xrt)


@pytest.mark.asyncio
async def test_ensure_non_boolean_condition(xrt):
    """Test that ensure requires boolean conditions."""
    with pytest.raises(XegaSyntaxError):
        await eval_line("ensure('not a boolean')", 1, xrt)


@pytest.mark.asyncio
async def test_ensure_max_failures(xrt):
    """Test that ensure respects MAX_ENSURE_FAILURES limit."""
    game_code = """
    elicit(s, 10)
    ensure(s == 'impossible_to_guess')
    """

    # This should eventually throw
    game_results = await play_game(
        game_code, xrt, auto_replay=False, max_steps=MAX_ENSURE_FAILURES + 5
    )

    assert len(game_results) == 0


@pytest.mark.asyncio
async def test_ensure_with_complex_expressions(xrt):
    """Test ensure with complex boolean expressions."""
    await eval_line("assign(s1='hello', s2='world', s3='hello world')", 1, xrt)
    await eval_line("elicit(x, 10)", 2, xrt)

    # Complex condition that should pass
    result = await eval_line("ensure((s1 + ' ' + s2) == s3, len(s1) < len(s3))", 3, xrt)
    assert result is None

    # Complex condition that should fail
    result = await eval_line("ensure(len(s1) > len(s3) or s2 not in s3)", 4, xrt)
    assert isinstance(result, XFlag)


@pytest.mark.asyncio
async def test_ensure_with_validated_bool(xrt):
    """Test that ensure works with ValidatedBool from xent comparisons."""
    await eval_line(
        "assign(s1='test test test test', s2='test test test test')", 1, xrt
    )
    await eval_line("elicit(x, 10)", 2, xrt)

    # xent comparisons return ValidatedBool
    result = await eval_line("ensure(xent(s1) == xent(s2))", 3, xrt)
    assert result is None

    # Test with combined ValidatedBool conditions
    result = await eval_line(
        "ensure(xent(s1) < xent('a very long string asefsadf asdfasdfasdf asdfasdfadsf'), xent(s2) > 0)",
        4,
        xrt,
    )
    assert result is None
