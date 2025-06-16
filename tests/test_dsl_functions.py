import pytest

from tests.conftest import FAKE_GAME_CONFIG
from xega.runtime.default_players import MockXGP
from xega.runtime.execution import eval_line
from xega.runtime.judge import Judge
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals

# STRING OPERATION TESTS


@pytest.mark.asyncio
async def test_string_concatenation(xrt):
    """Test string concatenation with + operator."""
    await eval_line("assign(s1='hello', s2='world')", 1, xrt)
    await eval_line("assign(s3=s1 + ' ' + s2)", 2, xrt)

    assert str(xrt.local_vars["s3"]) == "hello world"


@pytest.mark.asyncio
async def test_string_before_operator(xrt):
    """Test // operator (substring before delimiter)."""
    await eval_line("assign(s='hello world again')", 1, xrt)

    # Test basic case
    await eval_line("assign(s1=s // 'world')", 2, xrt)
    assert str(xrt.local_vars["s1"]) == "hello "

    # Test when delimiter is at start
    await eval_line("assign(s1=s // 'hello')", 3, xrt)
    assert str(xrt.local_vars["s1"]) == ""

    # Test when delimiter is not found
    await eval_line("assign(s1=s // 'xyz')", 4, xrt)
    assert str(xrt.local_vars["s1"]) == "hello world again"

    # Test with empty delimiter
    await eval_line("assign(s1=s // '')", 5, xrt)
    assert str(xrt.local_vars["s1"]) == "hello world again"


@pytest.mark.asyncio
async def test_string_after_operator(xrt):
    """Test % operator (substring after delimiter)."""
    await eval_line("assign(s='hello world again')", 1, xrt)

    # Test basic case
    await eval_line("assign(s1=s % 'world')", 2, xrt)
    assert str(xrt.local_vars["s1"]) == " again"

    # Test when delimiter is at end
    await eval_line("assign(s1=s % 'again')", 3, xrt)
    assert str(xrt.local_vars["s1"]) == ""

    # Test when delimiter is not found
    await eval_line("assign(s1=s % 'xyz')", 4, xrt)
    assert str(xrt.local_vars["s1"]) == ""

    # Test with empty delimiter
    await eval_line("assign(s1=s % '')", 5, xrt)
    assert str(xrt.local_vars["s1"]) == ""


# FUNCTION TESTS


@pytest.mark.asyncio
async def test_story_function(xrt):
    await eval_line("assign(s1=story())", 1, xrt)
    await eval_line("assign(s2=story())", 1, xrt)

    assert len(str(xrt.local_vars["s1"])) > 0
    assert len(str(xrt.local_vars["s2"])) > 0
    assert str(xrt.local_vars["s1"]) != str(xrt.local_vars["s2"])

    # Make sure we can get a lot of stories without issues
    for i in range(100):
        await eval_line("assign(s=story(), s1=story())", i, xrt)


@pytest.mark.asyncio
async def test_story_map_seed():
    game_config = FAKE_GAME_CONFIG.copy()
    game_config["map_seed"] = "test_seed_99"
    player = MockXGP("black", {}, game_config)
    locals = build_locals([player], game_config)
    model_utils = Judge("gpt2")
    globals = build_globals(model_utils, game_config["map_seed"])
    xrt = XegaRuntime([player], locals, globals)

    # Make sure we can get a lot of stories without issues
    for i in range(100):
        await eval_line("assign(s=story(), s1=story())", i, xrt)


@pytest.mark.asyncio
async def test_remove_common_words_function(xrt):
    """Test remove_common_words() function."""
    await eval_line("assign(s1='the cat and the dog', s2='the dog and a bird')", 1, xrt)
    await eval_line("assign(s3=remove_common_words(s1, s2))", 2, xrt)

    s1_cleaned = xrt.local_vars["s3"]
    assert "cat" in str(s1_cleaned)
    assert "dog" not in str(s1_cleaned)


# XENT FUNCTION TESTS


@pytest.mark.asyncio
async def test_xent_basic(xrt):
    """Test basic xent() function."""
    score_before = xrt.local_vars["black"].score
    await eval_line("reward(black, xent('hello world'))", 1, xrt)
    first_score = xrt.local_vars["black"].score - score_before
    await eval_line(
        "reward(black, xent('hello world hello world hello world'))", 2, xrt
    )
    second_score = xrt.local_vars["black"].score - score_before - first_score

    assert second_score > first_score


@pytest.mark.asyncio
async def test_xent_with_prefix(xrt):
    """Test xent() with prefix (| operator)."""
    score_before = xrt.local_vars["black"].score
    await eval_line("reward(black, xent('hello world'))", 1, xrt)
    first_score = xrt.local_vars["black"].score - score_before
    await eval_line(
        "reward(black, xent('hello world' | 'first program print text'))", 2, xrt
    )
    second_score = xrt.local_vars["black"].score - score_before - first_score

    assert second_score < first_score


@pytest.mark.asyncio
async def test_nex_function(xrt):
    """Test basic xent() function."""
    score_before = xrt.local_vars["black"].score
    await eval_line("reward(black, nex('hello world'))", 1, xrt)
    first_score = xrt.local_vars["black"].score - score_before
    await eval_line("reward(black, nex('hello world hello world hello world'))", 2, xrt)
    second_score = xrt.local_vars["black"].score - score_before - first_score

    assert second_score < first_score


@pytest.mark.asyncio
async def test_xed_function(xrt):
    """Test xed() function."""
    score_before = xrt.local_vars["black"].score
    await eval_line(
        "reward(black, xed('hello world' | 'first program print text'))", 1, xrt
    )
    score_after = xrt.local_vars["black"].score - score_before
    # Test that xed() gives a positive score
    assert score_after > score_before


# COMPLEX EXPRESSION TESTS


@pytest.mark.asyncio
async def test_function_in_conditionals(xrt):
    """Test using functions in ensure conditions."""
    await eval_line("assign(s='hello world')", 1, xrt)
    await eval_line("elicit(s1, 10)", 2, xrt)

    # Test length condition
    result = await eval_line("ensure(len(s) > 5)", 3, xrt)
    assert result is None  # Should pass

    # Test xent comparison
    result = await eval_line("ensure(xent(s) > xent('hi'))", 4, xrt)
    assert result is None  # Should pass
