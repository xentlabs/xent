import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from xega.cli.configure import (
    add_player_to_expanded_config,
    configure,
    remove_player_from_expanded_config,
)
from xega.common.xega_types import ExpandedXegaBenchmarkConfig, PlayerConfig


@pytest.fixture
def simple_expanded_config() -> ExpandedXegaBenchmarkConfig:
    """Provides a simple, expanded benchmark configuration for testing."""
    return {
        "config_type": "expanded_benchmark_config",
        "benchmark_id": "test-benchmark",
        "judge_model": "gpt-4",
        "npc_players": [],
        "num_variables_per_register": 4,
        "max_steps": 100,
        "auto_replay": True,
        "seed": "test-seed",
        "num_maps_per_game": 1,
        "games": [
            {
                "game": {"name": "game1", "code": "...", "map_seed": "map-seed-1"},
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
                "max_steps": 100,
                "auto_replay": True,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-1",
            },
            {
                "game": {"name": "game2", "code": "...", "map_seed": "map-seed-2"},
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
                "max_steps": 100,
                "auto_replay": True,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-2",
            },
            {
                "game": {"name": "game1", "code": "...", "map_seed": "map-seed-1"},
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
                "max_steps": 100,
                "auto_replay": True,
                "seed": "test-seed",
                "num_maps_per_game": 1,
                "map_seed": "map-seed-1",
            },
        ],
    }


def test_remove_player_from_expanded_config_success(simple_expanded_config):
    """Test that a player is successfully removed from the config."""
    # Act
    config = remove_player_from_expanded_config(simple_expanded_config, "player-a")

    # Assert
    assert len(config["games"]) == 1, "Should remove all games for player-a"
    remaining_player_ids = {game["players"][0]["id"] for game in config["games"]}
    assert remaining_player_ids == {"player-b"}


def test_remove_player_from_expanded_config_player_not_found(
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


def test_remove_player_cmd_success(tmp_path, simple_expanded_config):
    """Test the 'remove-player' CLI command with a valid config."""
    # Arrange
    runner = CliRunner()
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(simple_expanded_config, f)

    # Act
    result = runner.invoke(
        configure,
        ["remove-player", str(config_path), "--model", "player-a"],
        catch_exceptions=False,
    )

    # Assert
    assert result.exit_code == 0
    assert "Successfully removed player: player-a" in result.output

    with open(config_path) as f:
        updated_config = json.load(f)
    assert len(updated_config["games"]) == 1


def test_remove_player_cmd_not_expanded_config(tmp_path):
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
        "Error: This command only works with expanded configurations." in result.output
    )


def test_add_player_to_expanded_config(simple_expanded_config):
    """Test adding a new player to an expanded config."""
    # Arrange
    new_player = PlayerConfig(
        id="player-c", name="black", player_type="default", options={}
    )

    # Act
    config = add_player_to_expanded_config(simple_expanded_config, new_player)

    # Assert
    assert len(config["games"]) == 5, "Should add 2 new games for the new player"
    player_ids = [game["players"][0]["id"] for game in config["games"]]
    assert player_ids.count("player-c") == 2, "New player should have 2 games"


def test_add_player_cmd_success(tmp_path, simple_expanded_config):
    """Test the 'add-player' CLI command."""
    # Arrange
    runner = CliRunner()
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(simple_expanded_config, f)

    # Act
    result = runner.invoke(
        configure,
        ["add-player", str(config_path), "--model", "player-c"],
        catch_exceptions=False,
    )

    # Assert
    assert result.exit_code == 0
    assert "Added player: player-c" in result.output

    with open(config_path) as f:
        updated_config = json.load(f)
    assert len(updated_config["games"]) == 5
