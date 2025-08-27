import json
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from xega.cli.configure import (
    add_player_to_expanded_config,
    configure,
    games_from_dir,
    remove_player_from_expanded_config,
)
from xega.cli.run import check_version
from xega.common.version import get_xega_version
from xega.common.xega_types import ExpandedXegaBenchmarkConfig, PlayerConfig


@pytest.fixture
def simple_expanded_config() -> ExpandedXegaBenchmarkConfig:
    """Provides a simple, expanded benchmark configuration for testing."""
    return {
        "config_type": "expanded_benchmark_config",
        "benchmark_id": "test-benchmark",
        "xega_version": "0.1.0-dev",
        "judge_model": "gpt-4",
        "npc_players": [],
        "num_variables_per_register": 4,
        "num_rounds_per_game": 30,
        "seed": "test-seed",
        "num_maps_per_game": 1,
        "games": [
            {
                "game": {
                    "name": "game1",
                    "code": "...",
                    "presentation_function": "...",
                    "map_seed": "map-seed-1",
                },
                "players": [
                    {
                        "id": "player-a",
                        "name": "black",
                        "player_type": "default",
                        "options": {},
                    }
                ],
                "judge_model": "gpt-4",
                "npc_players": [],
                "num_variables_per_register": 4,
                "num_rounds_per_game": 30,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-1",
            },
            {
                "game": {
                    "name": "game2",
                    "code": "...",
                    "presentation_function": "...",
                    "map_seed": "map-seed-2",
                },
                "players": [
                    {
                        "id": "player-a",
                        "name": "black",
                        "player_type": "default",
                        "options": {},
                    }
                ],
                "judge_model": "gpt-4",
                "npc_players": [],
                "num_variables_per_register": 4,
                "num_rounds_per_game": 30,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-2",
            },
            {
                "game": {
                    "name": "game1",
                    "code": "...",
                    "presentation_function": "...",
                    "map_seed": "map-seed-1",
                },
                "players": [
                    {
                        "id": "player-b",
                        "name": "black",
                        "player_type": "default",
                        "options": {},
                    }
                ],
                "judge_model": "gpt-4",
                "npc_players": [],
                "num_variables_per_register": 4,
                "num_rounds_per_game": 30,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-1",
            },
        ],
    }


class TestConfigureCommands:
    """Test configure CLI command functions"""

    def test_remove_player_success(self, tmp_path, simple_expanded_config):
        """Test removing a player both directly and via CLI command."""
        # Test 1: Direct function call
        config_direct = remove_player_from_expanded_config(
            deepcopy(simple_expanded_config), "player-a"
        )
        assert len(config_direct["games"]) == 1, "Should remove all games for player-a"
        remaining_player_ids = {
            game["players"][0]["id"] for game in config_direct["games"]
        }
        assert remaining_player_ids == {"player-b"}

        # Test 2: Via CLI command
        runner = CliRunner()
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(simple_expanded_config, f)

        result = runner.invoke(
            configure,
            ["remove-player", str(config_path), "--model", "player-a"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Successfully removed player: player-a" in result.output

        with open(config_path) as f:
            updated_config = json.load(f)
        assert len(updated_config["games"]) == 1

    def test_remove_player_from_expanded_config_player_not_found(
        self,
        simple_expanded_config,
    ):
        """Test that the config remains unchanged if the player ID is not found."""
        # Arrange
        original_config = deepcopy(simple_expanded_config)

        # Act
        with patch("click.echo") as mock_echo:
            config = remove_player_from_expanded_config(
                simple_expanded_config, "non-existent-player"
            )

            # Assert
            assert config == original_config, "Config should not be modified"
            mock_echo.assert_called_with(
                "Warning: Player with ID 'non-existent-player' not found.", err=True
            )

    def test_remove_player_cmd_not_expanded_config(self, tmp_path):
        """Test that the 'remove-player' command fails on a non-expanded config."""
        # Arrange
        runner = CliRunner()
        config_path = tmp_path / "config.json"
        config_data = {"config_type": "short_benchmark_config"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Act
        result = runner.invoke(
            configure,
            ["remove-player", str(config_path), "--model", "player-a"],
        )

        # Assert
        assert result.exit_code != 0
        assert (
            "Error: This command only works with expanded configurations."
            in result.output
        )

    def test_add_player_success(self, tmp_path, simple_expanded_config):
        """Test adding a player both directly and via CLI command."""
        # Test 1: Direct function call
        new_player = PlayerConfig(
            id="player-c", name="black", player_type="default", options={}
        )
        config_direct = add_player_to_expanded_config(
            deepcopy(simple_expanded_config), new_player
        )
        assert len(config_direct["games"]) == 5, (
            "Should add 2 new games for the new player"
        )
        player_ids = [game["players"][0]["id"] for game in config_direct["games"]]
        assert player_ids.count("player-c") == 2, "New player should have 2 games"

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
        assert result.exit_code == 0
        assert "Added player: player-c" in result.output

        with open(config_path) as f:
            updated_config = json.load(f)
        assert len(updated_config["games"]) == 5


class TestCLIPresentationIntegration:
    """Test CLI integration with presentation functions"""

    def test_games_from_dir_comprehensive(self):
        """Test games_from_dir with various presentation scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Scenario 1: Game without presentation
            simple_path = Path(temp_dir) / "simple.xega"
            simple_path.write_text('assign(s="test")\nreveal(black, s)')

            # Scenario 2: Game with valid presentation
            custom_path = Path(temp_dir) / "custom.xega"
            custom_path.write_text('assign(s="custom")\nreveal(black, s)')
            custom_pres_path = Path(temp_dir) / "custom_presentation.py"
            custom_pres_path.write_text("""def present(state, history):
    return "Custom presentation"
""")

            # Scenario 3: Game with non-standard presentation (warnings)
            warning_path = Path(temp_dir) / "warning.xega"
            warning_path.write_text('assign(s="warning")')
            warning_pres_path = Path(temp_dir) / "warning_presentation.py"
            warning_pres_path.write_text("""def present(game_state, events):  # Non-standard names
    return "Works with warnings"
""")

            # Scenario 4: Another game without presentation to test mixed scenario
            another_path = Path(temp_dir) / "another.xega"
            another_path.write_text('assign(s="another")')

            games = games_from_dir(temp_dir)
            assert len(games) == 4

            # Verify each game
            simple = next(g for g in games if g["name"] == "simple")
            assert simple["code"] == 'assign(s="test")\nreveal(black, s)'
            assert simple.get("presentation_function") is None

            custom = next(g for g in games if g["name"] == "custom")
            assert custom["code"] == 'assign(s="custom")\nreveal(black, s)'
            assert custom["presentation_function"] is not None
            assert "Custom presentation" in custom["presentation_function"]
            assert "def present(state, history):" in custom["presentation_function"]

            warning = next(g for g in games if g["name"] == "warning")
            assert warning["code"] == 'assign(s="warning")'
            assert warning["presentation_function"] is not None
            assert "Works with warnings" in warning["presentation_function"]

            another = next(g for g in games if g["name"] == "another")
            assert another["code"] == 'assign(s="another")'
            assert another.get("presentation_function") is None


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
        config["xega_version"] = "99.99.99"

        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            check_version(config, ignore_version_mismatch=False)
        assert exc_info.value.code == 1

    def test_check_version_mismatch_ignored(self, simple_expanded_config, caplog):
        """Test check_version with ignore flag allows mismatch"""
        import logging

        # Add different version to config
        config = deepcopy(simple_expanded_config)
        config["xega_version"] = "99.99.99"

        # Should not raise exception when ignored
        with caplog.at_level(logging.WARNING):
            check_version(config, ignore_version_mismatch=True)

        # Should have warning in logs
        assert "mismatch" in caplog.text.lower()
        assert "99.99.99" in caplog.text

    def test_check_version_missing_version(self, simple_expanded_config, caplog):
        """Test check_version with missing version field (backward compatibility)"""
        import logging

        # Config without xega_version field
        config = deepcopy(simple_expanded_config)
        if "xega_version" in config:
            del config["xega_version"]

        # Should not raise exception (backward compatible)
        with caplog.at_level(logging.WARNING):
            check_version(config, ignore_version_mismatch=False)

        # Should have warning about missing version
        assert "no version" in caplog.text.lower() or "warning" in caplog.text.lower()

    def test_configure_expand_includes_version(self, tmp_path):
        """Test that configure creates config with version when expanded"""
        from xega.benchmark.expand_benchmark import expand_benchmark_config
        from xega.common.xega_types import XegaBenchmarkConfig

        # Create a simple benchmark config
        config: XegaBenchmarkConfig = {
            "config_type": "short_benchmark_config",
            "games": [
                {
                    "name": "test_game",
                    "code": "assign(s='test')\nreveal(black, s)",
                    "presentation_function": None,
                }
            ],
            "players": [
                [{"name": "black", "id": "gpt2", "player_type": "hf", "options": None}]
            ],
            "benchmark_id": "test-version-check",
            "judge_model": "gpt2",
            "npc_players": [],
            "num_variables_per_register": 4,
            "num_rounds_per_game": 1,
            "seed": "test",
            "num_maps_per_game": 1,
        }

        # Save the config
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Expand the config (this is what configure --expand does internally)
        expanded = expand_benchmark_config(config)

        # Verify version is included
        assert "xega_version" in expanded
        assert expanded["xega_version"] == get_xega_version()
