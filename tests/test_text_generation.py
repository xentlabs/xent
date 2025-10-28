from unittest.mock import Mock

import pytest

from xent.benchmark.expand_benchmark import (
    expand_game_config,
    preprocess_dsl_code,
)
from xent.common.configuration_types import GameConfig
from xent.common.errors import XentSyntaxError
from xent.runtime.judge import Judge


@pytest.mark.integration
def test_generate_list_smoke():
    """Smoke test for JudgeGenerator.generate_list.

    Ensures the method returns a non-empty list of strings
    with at most the requested length and no obvious artifacts.
    """
    # Use a small, widely available model to keep the test light.
    try:
        judge = Judge("Qwen/Qwen3-14B-Base")
    except Exception as e:
        pytest.skip(f"Skipping generate_list smoke test (model unavailable): {e}")

    items = judge.text_generator.generate_list(
        "english nouns that have a prounoun of 'it' ie neuter objects", length=5
    )

    assert isinstance(items, list)
    assert len(items) == 5
    assert all(isinstance(x, str) and x.strip() for x in items)
    # No duplicates (case-insensitive) in the small sample
    assert len({x.strip().lower() for x in items}) == len(items)
    # Avoid leaking sentinel markers
    for x in items:
        lx = x.strip().lower()
        assert not lx.startswith("begin list")
        assert not lx.startswith("end list")


class TestExpandConfig:
    """Tests for expand_game_config and related functionality."""

    @pytest.fixture
    def mock_judge(self):
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
    def simple_game_config(self):
        """Create a simple game config with a single story() call"""
        return GameConfig(
            name="test_simple_story",
            code="""
                assign(s=story())
                reveal(s)
                elicit(x, 10)
                reward(xent(x | s))
            """,
            presentation_function="",
        )

    @pytest.fixture
    def multi_story_game_config(self):
        """Create a game config with multiple story() calls"""
        return GameConfig(
            name="test_multi_story",
            code="""
                assign(s1=story(), s2=story())
                reveal(s1, s2)
                elicit(x, 20)
                reward(xent(x | s1))
                assign(s3=story())
                reward(-xent(s3 | x))
            """,
            presentation_function="",
        )

    @pytest.fixture
    def no_story_game_config(self):
        """Create a game config without any story() calls"""
        return GameConfig(
            name="test_no_story",
            code="""
                assign(s="This is a hardcoded string")
                reveal(s)
                elicit(x, 15)
                reward(xent(x | s))
            """,
            presentation_function="",
        )

    @pytest.fixture
    def complex_story_game_config(self):
        """Create a game config with story() in complex expressions"""
        return GameConfig(
            name="test_complex_story",
            code="""
                assign(s1="Introduction: ")
                assign(s=s1 + story())
                reveal(s)
                assign(s2=(story() + " " + story()))
                elicit(response, 25)
                reward(xent(response | s2))
            """,
            presentation_function="",
        )

    def test_expand_game_config_simple_story(self, simple_game_config, mock_judge):
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
        assert "reveal(s)" in expanded["code"]
        assert "elicit(x, 10)" in expanded["code"]
        assert "reward(xent(x | s))" in expanded["code"]

        # Verify judge methods were called
        mock_judge.set_seed.assert_not_called()
        mock_judge.generate_text.assert_called_once()

    def test_expand_game_config_multiple_stories(
        self, multi_story_game_config, mock_judge
    ):
        """Test expansion of a game with multiple story() calls"""
        map_seed = "test_seed_1"

        expanded = expand_game_config(multi_story_game_config, map_seed, mock_judge)

        # Verify no story() calls remain
        assert "story()" not in expanded["code"]

        # Verify each story() was replaced with different content
        assert "Once upon a time in a distant galaxy..." in expanded["code"]
        assert "The mysterious stranger arrived at midnight..." in expanded["code"]
        assert "In the depths of the ancient forest..." in expanded["code"]

        # Should have generated 3 stories
        assert mock_judge.generate_text.call_count == 3

    def test_expand_game_config_no_story(self, no_story_game_config):
        """Test expansion of game with no story() calls"""
        mock_judge = Mock()
        expanded = expand_game_config(no_story_game_config, "seed", mock_judge)

        assert expanded["name"] == "test_no_story"
        assert "story()" not in expanded["code"]
        assert "This is a hardcoded string" in expanded["code"]

        # No generation should occur
        mock_judge.generate_text.assert_not_called()

    def test_complex_story_composition(self, complex_story_game_config):
        """Test that complex expressions with story() are handled correctly"""
        mock_judge = Mock()
        mock_judge.generate_text.return_value = "Generated story content"

        expanded = expand_game_config(complex_story_game_config, "seed", mock_judge)
        code = expanded["code"]

        # Should contain both stories and composition preserved
        assert code.count("Generated story content") >= 2
        assert "assign(s=s1 +" in code
        assert "assign(s2=" in code

    def test_preprocess_dsl_code(self):
        """Direct tests of preprocess_dsl_code behavior"""
        mock_judge = Mock()
        mock_judge.generate_text.return_value = "Test story"

        code = "assign(x=story())\nreveal(x)\nelicit(10)"
        result = preprocess_dsl_code(code, mock_judge)

        # All story() calls replaced and code structure preserved
        assert "story()" not in result
        assert "'Test story'" in result
        assert "reveal(x)" in result
        assert "elicit(10)" in result

        # Each line should be properly transformed
        lines = result.splitlines()
        assert lines[0] == "assign(x='Generated story content')" or (
            lines[0] == "assign(x='Test story')"
        )
        assert lines[1] == "reveal(x)"
        assert lines[2] == "elicit(10)"

    def test_story_rewriter_only_replaces_story_function(self):
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

    def test_expand_game_config_empty_code(self):
        """Test expansion of game with empty code"""
        game_config = GameConfig(name="test_empty", code="", presentation_function="")

        mock_judge = Mock()
        map_seed = "test_seed"

        expanded = expand_game_config(game_config, map_seed, mock_judge)

        assert expanded["name"] == "test_empty"
        assert expanded["code"] == ""
        assert expanded["map_seed"] == map_seed

        # No story generation should occur
        mock_judge.generate_text.assert_not_called()

    def test_comments_and_formatting_comprehensive(self):
        """Comprehensive test for comment preservation and formatting in all scenarios."""
        # Test 1: Full-line comments
        judge1 = Mock()
        judge1.generate_text.return_value = "Once upon a time in a distant galaxy..."
        code_full_line = """
# This is a full-line comment.
assign(s=story())
# Another comment
        """
        processed_full = preprocess_dsl_code(code_full_line, judge1)
        assert "# This is a full-line comment." in processed_full
        assert "assign(s='Once upon a time in a distant galaxy...')" in processed_full
        assert "# Another comment" in processed_full

        # Test 2: Inline comments
        judge2 = Mock()
        judge2.generate_text.return_value = "Once upon a time in a distant galaxy..."
        code_inline = "assign(s=story())  # This is an inline comment."
        processed_inline = preprocess_dsl_code(code_inline, judge2)
        assert "assign(s='Once upon a time in a distant galaxy...')" in processed_inline
        assert "# This is an inline comment." in processed_inline

        # Test 3: Comment-only lines
        judge3 = Mock()
        code_comment_only = "# Just a comment"
        processed_comment_only = preprocess_dsl_code(code_comment_only, judge3)
        assert code_comment_only in processed_comment_only
        judge3.generate_text.assert_not_called()

        # Test 4: Empty lines preserved
        judge4 = Mock()
        judge4.generate_text.return_value = "Once upon a time in a distant galaxy..."
        code_empty_lines = """
assign(s=story())

reveal(s)
        """
        processed_empty = preprocess_dsl_code(code_empty_lines, judge4)
        assert "assign(s='Once upon a time in a distant galaxy...')" in processed_empty
        assert "\n\n" in processed_empty
        assert "reveal(s)" in processed_empty

        # Test 5: Mixed comments and code
        judge5 = Mock()
        judge5.generate_text.side_effect = [
            "Once upon a time in a distant galaxy...",
            "The mysterious stranger arrived at midnight...",
        ]
        code_mixed = """
# Header comment
assign(s1=story())  # First story
assign(s2=story())  # Second story

# Footer comment
        """
        processed_mixed = preprocess_dsl_code(code_mixed, judge5)
        assert "# Header comment" in processed_mixed
        assert "assign(s1='Once upon a time in a distant galaxy...')" in processed_mixed
        assert (
            "assign(s2='The mysterious stranger arrived at midnight...')"
            in processed_mixed
        )
        assert "# Footer comment" in processed_mixed

    def test_generate_list_rewrite_positional(self):
        """generate_list(prompt, length) is rewritten into a literal list."""
        mock_judge = Mock()

        def gl_side_effect(prompt: str, length: int) -> list[str]:
            assert prompt == "colors"
            assert length == 3
            return ["red", "blue", "green"]

        mock_judge.generate_list.side_effect = gl_side_effect

        code = 'assign(l=generate_list("colors", 3))'
        rewritten = preprocess_dsl_code(code, mock_judge)
        assert "generate_list(" not in rewritten
        assert "assign(l=[" in rewritten
        # Basic presence checks for returned items
        assert "red" in rewritten and "blue" in rewritten and "green" in rewritten

    def test_generate_list_rejects_keywords(self):
        """generate_list with keyword args should raise a syntax error."""
        mock_judge = Mock()
        code = 'assign(l=generate_list(length=2, prompt="animals"))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code, mock_judge)

    def test_generate_list_rejects_wrong_arity(self):
        mock_judge = Mock()
        code = 'assign(l=generate_list("colors"))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code, mock_judge)

        code2 = 'assign(l=generate_list("colors", 3, 4))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code2, mock_judge)

    def test_generate_list_rejects_wrong_types(self):
        mock_judge = Mock()
        code = "assign(l=generate_list(123, 3))"
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code, mock_judge)

        code2 = 'assign(l=generate_list("colors", "five"))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code2, mock_judge)

    def test_generate_list_accepts_float_length(self):
        """Numeric literal length (float) is accepted and cast to int."""
        mock_judge = Mock()

        def gl(prompt: str, length: int) -> list[str]:
            # Ensure length was cast to int
            assert isinstance(length, int) and length == 3
            assert prompt == "colors"
            return ["red", "blue", "green"]

        mock_judge.generate_list.side_effect = gl
        code = 'assign(l=generate_list("colors", 3.0))'
        rewritten = preprocess_dsl_code(code, mock_judge)
        assert "assign(l=[" in rewritten
        assert "red" in rewritten and "blue" in rewritten and "green" in rewritten

    def test_generate_list_rejects_nonliteral_prompt(self):
        mock_judge = Mock()
        code = 'assign(p="colors")\nassign(l=generate_list(p, 5))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code, mock_judge)

    def test_generate_list_rejects_swapped_types(self):
        mock_judge = Mock()
        code = 'assign(l=generate_list(5, "colors"))'
        with pytest.raises(XentSyntaxError):
            preprocess_dsl_code(code, mock_judge)
