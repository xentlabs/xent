import json
import logging
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest
from click.testing import CliRunner

from xega.cli.configure import (
    add_player_to_config,
    configure,
    games_from_paths,
    remove_player_from_config,
)
from xega.cli.run import check_version
from xega.common.configuration_types import (
    ExpandedXegaBenchmarkConfig,
    PlayerConfig,
)
from xega.common.version import get_xega_version
from xega.presentation.executor import get_default_presentation


@pytest.fixture
def simple_expanded_config() -> ExpandedXegaBenchmarkConfig:
    """Provides a simple, expanded benchmark configuration for testing."""
    return {
        "config_type": "expanded_xega_config",
        "metadata": {
            "benchmark_id": "test-benchmark",
            "xega_version": get_xega_version(),
            "judge_model": "gpt-4",
            "num_rounds_per_game": 30,
            "seed": "test-seed",
        },
        "games": [
            {
                "name": "game1",
                "code": "...",
                "presentation_function": "...",
            },
            {
                "name": "game2",
                "code": "...",
                "presentation_function": "...",
            },
        ],
        "maps": [
            {
                "name": "game1",
                "code": "...",
                "presentation_function": "...",
                "map_seed": "map-seed-1",
            },
            {
                "name": "game2",
                "code": "...",
                "presentation_function": "...",
                "map_seed": "map-seed-2",
            },
        ],
        "players": [
            {
                "id": "player-a",
                "name": "black",
                "player_type": "default",
                "options": {},
            },
            {
                "id": "player-b",
                "name": "black",
                "player_type": "default",
                "options": {},
            },
        ],
    }


class TestConfigureCommands:
    """Test configure CLI command functions"""

    def test_remove_player_success(self, tmp_path, simple_expanded_config):
        """Test removing a player both directly and via CLI command."""
        # Test 1: Direct function call
        config_direct = remove_player_from_config(
            deepcopy(simple_expanded_config), "player-a"
        )
        assert len(config_direct["players"]) == 1, (
            "Should remove all games for player-a"
        )
        assert config_direct["players"][0]["id"] == "player-b"

        # Test 2: Via CLI command
        runner = CliRunner()
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(simple_expanded_config, f)

        result = runner.invoke(
            configure,
            ["remove-player", str(config_path), "--player-id", "player-a"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, "Got non zero error code"
        assert "Successfully removed player: player-a" in result.output

        with open(config_path) as f:
            updated_config = json.load(f)
        assert len(updated_config["players"]) == 1, (
            "Should remove all games for player-a"
        )
        assert updated_config["players"][0]["id"] == "player-b"

    def test_remove_player_from_expanded_config_player_not_found(
        self,
        simple_expanded_config,
    ):
        """Test that the config remains unchanged if the player ID is not found."""
        # Arrange
        original_config = deepcopy(simple_expanded_config)

        # Act
        config = remove_player_from_config(
            simple_expanded_config, "non-existent-player"
        )

        # Assert
        assert config == original_config, "Config should not be modified"

    def test_add_player_success(self, tmp_path, simple_expanded_config):
        """Test adding a player both directly and via CLI command."""
        # Test 1: Direct function call
        new_player = PlayerConfig(
            id="player-c", name="black", player_type="default", options={}
        )
        config_direct = add_player_to_config(
            deepcopy(simple_expanded_config), new_player
        )
        assert len(config_direct["players"]) == 3

        # Test 2: Via CLI command
        runner = CliRunner()
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(simple_expanded_config, f)

        result = runner.invoke(
            configure,
            ["add-player", str(config_path), "--model", "player-c"],
            catch_exceptions=False,
        )
        print(result.output)
        assert result.exit_code == 0
        assert "Added player: player-c" in result.output

        with open(config_path) as f:
            updated_config = json.load(f)
        assert len(updated_config["players"]) == 3


class TestCLIPresentationIntegration:
    """Test CLI integration with presentation functions"""

    def test_games_from_paths_comprehensive(self):
        """Test games_from_paths with various presentation scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir_path:
            temp_dir = Path(temp_dir_path)
            # Scenario 1: Game without presentation
            simple_path = temp_dir / "simple.xega"
            simple_path.write_text('assign(s="test")\nreveal(black, s)')

            # Scenario 2: Game with valid presentation
            custom_path = temp_dir / "custom.xega"
            custom_path.write_text('assign(s="custom")\nreveal(black, s)')
            custom_pres_path = temp_dir / "custom_presentation.py"
            custom_pres_path.write_text("""def present(state, history, metadata):
    return "Custom presentation"
""")

            # Scenario 3: Game with non-standard presentation (warnings)
            warning_path = temp_dir / "warning.xega"
            warning_path.write_text('assign(s="warning")')
            warning_pres_path = temp_dir / "warning_presentation.py"
            warning_pres_path.write_text("""def present(game_state, events, metadata):  # Non-standard names
    return "Works with warnings"
""")

            # Scenario 4: Another game without presentation to test mixed scenario
            another_path = temp_dir / "another.xega"
            another_path.write_text('assign(s="another")')

            # Test that duplicate games are not added
            games = games_from_paths([simple_path, temp_dir])
            assert len(games) == 4

            # Verify each game
            simple = next(g for g in games if g["name"] == "simple")
            assert simple["code"] == 'assign(s="test")\nreveal(black, s)'
            assert simple["presentation_function"] == get_default_presentation()

            custom = next(g for g in games if g["name"] == "custom")
            assert custom["code"] == 'assign(s="custom")\nreveal(black, s)'
            assert custom["presentation_function"] is not None
            assert "Custom presentation" in custom["presentation_function"]
            assert (
                "def present(state, history, metadata):"
                in custom["presentation_function"]
            )

            warning = next(g for g in games if g["name"] == "warning")
            assert warning["code"] == 'assign(s="warning")'
            assert warning["presentation_function"] is not None
            assert "Works with warnings" in warning["presentation_function"]

            another = next(g for g in games if g["name"] == "another")
            assert another["code"] == 'assign(s="another")'
            assert another["presentation_function"] == get_default_presentation()


class TestVersionChecking:
    """Test version checking functionality in CLI"""

    def test_check_version_matching(self, simple_expanded_config):
        """Test check_version with matching versions"""

        # Add current version to config
        config = deepcopy(simple_expanded_config)
        config["xega_version"] = get_xega_version()

        # Should not raise any exception
        check_version(config, ignore_version_mismatch=False)

    def test_check_version_mismatch_raises(self, simple_expanded_config):
        """Test check_version raises SystemExit on version mismatch"""

        # Add different version to config
        config = deepcopy(simple_expanded_config)
        config["metadata"]["xega_version"] = "99.99.99"

        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            check_version(config, ignore_version_mismatch=False)
        assert exc_info.value.code == 1

    def test_check_version_mismatch_ignored(self, simple_expanded_config, caplog):
        """Test check_version with ignore flag allows mismatch"""

        # Add different version to config
        config = deepcopy(simple_expanded_config)
        config["metadata"]["xega_version"] = "99.99.99"

        # Should not raise exception when ignored
        with caplog.at_level(logging.WARNING):
            check_version(config, ignore_version_mismatch=True)

        # Should have warning in logs
        assert "mismatch" in caplog.text.lower()
        assert "99.99.99" in caplog.text
