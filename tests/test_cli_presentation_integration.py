"""
Integration tests for CLI presentation function support.
"""

import tempfile
from pathlib import Path

from xega.cli.configure import games_from_dir


class TestCLIPresentationIntegration:
    """Test CLI integration with presentation functions"""

    def test_games_from_dir_without_presentation(self):
        """Test reading games without presentation functions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple game without presentation
            game_path = Path(temp_dir) / "simple.xega"
            game_path.write_text('assign(s="test")\nreveal(black, s)')

            games = games_from_dir(temp_dir)

            assert len(games) == 1
            assert games[0]["name"] == "simple"
            assert games[0]["code"] == 'assign(s="test")\nreveal(black, s)'
            assert games[0].get("presentation_function") is None

    def test_games_from_dir_with_valid_presentation(self):
        """Test reading games with valid presentation functions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create game file
            game_path = Path(temp_dir) / "custom.xega"
            game_path.write_text('assign(s="test")\nreveal(black, s)')

            # Create presentation function with new naming convention
            presentation_path = Path(temp_dir) / "custom_presentation.py"
            presentation_path.write_text("""
def present(state, history):
    return "Custom presentation"
""")

            games = games_from_dir(temp_dir)

            assert len(games) == 1
            assert games[0]["name"] == "custom"
            assert games[0]["presentation_function"] is not None
            assert "def present(state, history):" in games[0]["presentation_function"]

    def test_games_from_dir_mixed_games(self):
        """Test directory with mix of games with and without presentations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Game 1: with presentation
            game1_path = Path(temp_dir) / "game1.xega"
            game1_path.write_text('assign(s="game1")')

            # Create presentation function with new naming convention
            presentation_path1 = Path(temp_dir) / "game1_presentation.py"
            presentation_path1.write_text("""
def present(state, history):
    return "Game 1 presentation"
""")

            # Game 2: without presentation
            game2_path = Path(temp_dir) / "game2.xega"
            game2_path.write_text('assign(s="game2")')

            games = games_from_dir(temp_dir)

            assert len(games) == 2

            # Find games by name
            game1 = next(g for g in games if g["name"] == "game1")
            game2 = next(g for g in games if g["name"] == "game2")

            assert game1["presentation_function"] is not None
            assert "Game 1 presentation" in game1["presentation_function"]

            assert game2.get("presentation_function") is None

    def test_presentation_function_with_warnings(self):
        """Test that warnings are displayed but don't prevent processing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create game file
            game_path = Path(temp_dir) / "warning_game.xega"
            game_path.write_text('assign(s="test")')

            # Create presentation function with non-standard argument names using new naming convention
            presentation_path = Path(temp_dir) / "warning_game_presentation.py"
            presentation_path.write_text("""
def present(game_state, events):  # Non-standard names should generate warnings
    return "Works with warnings"
""")

            # Should succeed despite warnings
            games = games_from_dir(temp_dir)

            assert len(games) == 1
            assert games[0]["name"] == "warning_game"
            assert games[0]["presentation_function"] is not None
