from unittest.mock import Mock

import pytest

from xega.benchmark.expand_benchmark import expand_game_config, preprocess_dsl_code
from xega.common.xega_types import GameConfig


@pytest.fixture
def mock_judge():
    """Create a mock Judge that returns predictable story content"""
    judge = Mock()
    # Use side_effect to return different values on subsequent calls
    judge.generate_text.side_effect = [
        "Once upon a time in a distant galaxy...",
        "The mysterious stranger arrived at midnight...",
        "In the depths of the ancient forest...",
        "A brilliant scientist made a discovery...",
        "The dragon soared above the clouds...",
    ]
    judge.set_seed = Mock()
    return judge


@pytest.fixture
def simple_game_config():
    """Create a simple game config with a single story() call"""
    return GameConfig(
        name="test_simple_story",
        code="""
            assign(s=story())
            reveal(black, s)
            elicit(black, x, 10)
            reward(xent(x | s))
        """,
    )


@pytest.fixture
def multi_story_game_config():
    """Create a game config with multiple story() calls"""
    return GameConfig(
        name="test_multi_story",
        code="""
            assign(s1=story(), s2=story())
            reveal(black, s1, s2)
            elicit(black, x, 20)
            reward(xent(x | s1))
            assign(s3=story())
            reward(-xent(s3 | x))
        """,
    )


@pytest.fixture
def no_story_game_config():
    """Create a game config without any story() calls"""
    return GameConfig(
        name="test_no_story",
        code="""
            assign(s="This is a hardcoded string")
            reveal(black, s)
            elicit(black, x, 15)
            reward(xent(x | s))
        """,
    )


@pytest.fixture
def complex_story_game_config():
    """Create a game config with story() in complex expressions"""
    return GameConfig(
        name="test_complex_story",
        code="""
            assign(s1="Introduction: ")
            assign(s=s1 + story())
            reveal(black, s)
            assign(s2=(story() + " " + story()))
            elicit(black, response, 25)
            reward(xent(response | s2))
        """,
    )


def test_expand_game_config_simple_story(simple_game_config, mock_judge):
    """Test expansion of a simple game with one story() call"""
    map_seed = "test_seed_0"

    expanded = expand_game_config(simple_game_config, map_seed, mock_judge)

    # Verify structure
    assert isinstance(expanded, dict)
    assert expanded["name"] == "test_simple_story"
    assert expanded["map_seed"] == map_seed

    # Verify story() was replaced
    assert "story()" not in expanded["code"]
    assert "Once upon a time in a distant galaxy..." in expanded["code"]

    # Verify other code structure is preserved
    assert "assign(s=" in expanded["code"]
    assert "reveal(black, s)" in expanded["code"]
    assert "elicit(black, x, 10)" in expanded["code"]
    assert "reward(xent(x | s))" in expanded["code"]

    # Verify judge methods were called
    mock_judge.set_seed.assert_not_called()
    mock_judge.generate_text.assert_called_once()


def test_expand_game_config_multiple_stories(multi_story_game_config, mock_judge):
    """Test expansion of a game with multiple story() calls"""
    map_seed = "test_seed_1"

    expanded = expand_game_config(multi_story_game_config, map_seed, mock_judge)

    # Verify no story() calls remain
    assert "story()" not in expanded["code"]

    # Verify each story() was replaced with different content
    assert "Once upon a time in a distant galaxy..." in expanded["code"]
    assert "The mysterious stranger arrived at midnight..." in expanded["code"]
    assert "In the depths of the ancient forest..." in expanded["code"]

    # Verify structure is preserved
    assert "assign(s1=" in expanded["code"]
    assert "s2=" in expanded["code"]
    assert "reveal(black, s1, s2)" in expanded["code"]
    assert "assign(s3=" in expanded["code"]

    # Verify judge was called 3 times (for 3 story() calls)
    assert mock_judge.generate_text.call_count == 3


def test_expand_game_config_no_stories(no_story_game_config, mock_judge):
    """Test expansion of a game with no story() calls"""
    map_seed = "test_seed_2"

    expanded = expand_game_config(no_story_game_config, map_seed, mock_judge)

    # Verify structure
    assert expanded["name"] == "test_no_story"
    assert expanded["map_seed"] == map_seed

    # Verify hardcoded string is preserved
    assert "This is a hardcoded string" in expanded["code"]

    # Verify no story generation was called
    mock_judge.generate_text.assert_not_called()

    # Verify code structure is preserved
    assert "assign(s='This is a hardcoded string')" in expanded["code"]
    assert "reveal(black, s)" in expanded["code"]


def test_expand_game_config_complex_expressions(complex_story_game_config, mock_judge):
    """Test expansion of story() calls within complex expressions"""
    map_seed = "test_seed_3"

    expanded = expand_game_config(complex_story_game_config, map_seed, mock_judge)

    # Verify no story() calls remain
    assert "story()" not in expanded["code"]

    # Verify story calls were replaced in complex expressions
    assert "s1 + 'Once upon a time in a distant galaxy...'" in expanded["code"]
    assert "The mysterious stranger arrived at midnight..." in expanded["code"]
    assert "In the depths of the ancient forest..." in expanded["code"]

    # Verify expression structure is preserved
    assert "assign(s1='Introduction: ')" in expanded["code"]
    assert "assign(s2=" in expanded["code"]

    # Verify correct number of story generations
    assert mock_judge.generate_text.call_count == 3


def test_preprocess_dsl_code_preserves_formatting():
    """Test that preprocessing preserves line structure"""
    mock_judge = Mock()
    mock_judge.generate_text.return_value = "Generated story content"

    code = """assign(x=story())
reveal(player, x)
elicit(player, y, 10)"""

    result = preprocess_dsl_code(code, mock_judge)

    # Should have same number of lines
    assert len(result.splitlines()) == 3

    # Each line should be properly transformed
    lines = result.splitlines()
    assert lines[0] == "assign(x='Generated story content')"
    assert lines[1] == "reveal(player, x)"
    assert lines[2] == "elicit(player, y, 10)"


def test_story_rewriter_only_replaces_story_function():
    """Test that StoryRewriter only replaces story() calls, not other functions"""
    mock_judge = Mock()
    mock_judge.generate_text.return_value = "Test story"

    code_with_other_functions = """
        assign(a=story(), b=other_function(), c=yet_another())
        result = compute(story(), param)
    """

    result = preprocess_dsl_code(code_with_other_functions, mock_judge)

    # story() should be replaced
    assert "story()" not in result
    assert "'Test story'" in result

    # Other functions should remain unchanged
    assert "other_function()" in result
    assert "yet_another()" in result
    assert "compute(" in result


def test_expand_game_config_empty_code():
    """Test expansion of game with empty code"""
    game_config = GameConfig(name="test_empty", code="")

    mock_judge = Mock()
    map_seed = "test_seed"

    expanded = expand_game_config(game_config, map_seed, mock_judge)

    assert expanded["name"] == "test_empty"
    assert expanded["code"] == ""
    assert expanded["map_seed"] == map_seed

    # No story generation should occur
    mock_judge.generate_text.assert_not_called()


def test_expand_game_config_whitespace_preservation():
    """Test that code whitespace and indentation is handled correctly"""
    game_config = GameConfig(
        name="test_whitespace",
        code="""
            assign(s1=story())
                reveal(black, s1)
            elicit(black, x, 10)
        """,
    )

    mock_judge = Mock()
    mock_judge.generate_text.return_value = "Story text"

    expanded = expand_game_config(game_config, "seed", mock_judge)

    # Check that lines are stripped and reconstructed properly
    lines = expanded["code"].splitlines()
    assert all(line == line.strip() for line in lines if line)

    # Verify content
    assert "assign(s1='Story text')" in expanded["code"]
    assert "reveal(black, s1)" in expanded["code"]
    assert "elicit(black, x, 10)" in expanded["code"]
