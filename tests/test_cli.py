import json
import logging
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest
from click.testing import CliRunner

from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.cli.configure import (
    add_player_to_config,
    configure,
    parse_model_spec,
    remove_player_from_config,
)
from xent.cli.run import check_version
from xent.common.configuration_types import (
    ExpandedXentBenchmarkConfig,
    PlayerConfig,
)
from xent.common.game_discovery import discover_games_in_paths
from xent.common.version import get_xent_version
from xent.presentation.executor import get_default_presentation


@pytest.fixture
def simple_expanded_config() -> ExpandedXentBenchmarkConfig:
    """Provides a simple, expanded benchmark configuration for testing."""
    return {
        "config_type": "expanded_xent_config",
        "metadata": {
            "benchmark_id": "test-benchmark",
            "xent_version": get_xent_version(),
            "judge_model": "gpt-4",
            "num_rounds_per_game": 30,
            "seed": "test-seed",
            "store_full_player_interactions": False,
            "npcs": [],
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

    def test_store_full_interaction_flag_passthrough(self, tmp_path):
        """Ensure CLI flag sets metadata and survives expansion."""
        runner = CliRunner()
        output_path = tmp_path / "config.json"

        result = runner.invoke(
            configure,
            ["--store-full-interaction", "--output", str(output_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_path.exists()

        with output_path.open() as f:
            config = json.load(f)

        assert config["metadata"].get("store_full_player_interactions") is True

        expanded = expand_benchmark_config(config)
        assert expanded["metadata"].get("store_full_player_interactions") is True

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
            simple_path = temp_dir / "simple.xent"
            simple_path.write_text('assign(s="test")\nreveal(s)')

            # Scenario 2: Game with valid presentation
            custom_path = temp_dir / "custom.xent"
            custom_path.write_text('assign(s="custom")\nreveal(s)')
            custom_pres_path = temp_dir / "custom_presentation.py"
            custom_pres_path.write_text(
                """
from xent.presentation.sdk import ChatBuilder

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    b = ChatBuilder()
    b.user("Custom presentation")
    return b.render()
"""
            )

            # Scenario 3: Game with non-standard presentation (warnings)
            warning_path = temp_dir / "warning.xent"
            warning_path.write_text('assign(s="warning")')
            warning_pres_path = temp_dir / "warning_presentation.py"
            warning_pres_path.write_text(
                """
def present_turn(game_state, since_events, metadata, full_history=None, ctx=None):  # Non-standard names
    return [dict(role="user", content="Works with warnings")]
"""
            )

            # Scenario 4: Another game without presentation to test mixed scenario
            another_path = temp_dir / "another.xent"
            another_path.write_text('assign(s="another")')

            # Test that duplicate games are not added
            games = discover_games_in_paths([simple_path, temp_dir])
            assert len(games) == 4

            # Verify each game
            simple = next(g for g in games if g["name"] == "simple")
            assert simple["code"] == 'assign(s="test")\nreveal(s)'
            assert simple["presentation_function"] == get_default_presentation()

            custom = next(g for g in games if g["name"] == "custom")
            assert custom["code"] == 'assign(s="custom")\nreveal(s)'
            assert custom["presentation_function"] is not None
            assert "Custom presentation" in custom["presentation_function"]
            assert "def present_turn(" in custom["presentation_function"]

            warning = next(g for g in games if g["name"] == "warning")
            assert warning["code"] == 'assign(s="warning")'
            assert warning["presentation_function"] is not None
            assert "Works with warnings" in warning["presentation_function"]

            another = next(g for g in games if g["name"] == "another")
            assert another["code"] == 'assign(s="another")'
            assert another["presentation_function"] == get_default_presentation()


class TestModelParameterParsing:
    """Test URL-like model parameter parsing functionality"""

    def test_parse_model_spec_simple(self):
        """Test parsing simple model names without parameters"""
        model, params = parse_model_spec("gpt-4o")
        assert model == "gpt-4o"
        assert params == {}

        model, params = parse_model_spec("claude-3-5-sonnet")
        assert model == "claude-3-5-sonnet"
        assert params == {}

    def test_parse_model_spec_with_params(self):
        """Test parsing models with URL-like parameters"""
        # Single parameter
        model, params = parse_model_spec("gpt-4o?temperature=0.7")
        assert model == "gpt-4o"
        assert params == {"temperature": 0.7}

        # Multiple parameters with different types
        model, params = parse_model_spec(
            "claude-3-5-sonnet?max_tokens=8192&temperature=0&streaming=true"
        )
        assert model == "claude-3-5-sonnet"
        assert params == {"max_tokens": 8192, "temperature": 0, "streaming": True}

        # String parameters
        model, params = parse_model_spec("gpt-4o?reasoning_effort=high")
        assert model == "gpt-4o"
        assert params == {"reasoning_effort": "high"}

    def test_parse_model_spec_complex_values(self):
        """Test parsing with various value types"""
        # Float values
        model, params = parse_model_spec("model?top_p=0.95&presence_penalty=0.1")
        assert model == "model"
        assert params["top_p"] == 0.95
        assert params["presence_penalty"] == 0.1

        # Boolean values
        model, params = parse_model_spec("model?streaming=false&echo=true")
        assert model == "model"
        assert params["streaming"] is False
        assert params["echo"] is True

        # Null value
        model, params = parse_model_spec("model?stop=null")
        assert model == "model"
        assert params["stop"] is None

    def test_configure_with_model_params(self, tmp_path):
        """Test configure command with URL-like model parameters"""
        runner = CliRunner()
        output_path = tmp_path / "config.json"

        result = runner.invoke(
            configure,
            [
                "--model",
                "gpt-4o?temperature=0.7&reasoning_effort=high",
                "--model",
                "claude-3-5-sonnet?max_tokens=8192",
                "--output",
                str(output_path),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_path.exists()

        with open(output_path) as f:
            config = json.load(f)

        # Check first player (gpt-4o)
        gpt_player = next(p for p in config["players"] if p["id"] == "gpt-4o")
        assert gpt_player["options"]["model"] == "gpt-4o"
        assert gpt_player["options"]["provider"] == "openai"
        assert "request_params" in gpt_player["options"]
        assert gpt_player["options"]["request_params"]["temperature"] == 0.7
        assert gpt_player["options"]["request_params"]["reasoning_effort"] == "high"

        # Check second player (claude)
        claude_player = next(
            p for p in config["players"] if p["id"] == "claude-3-5-sonnet"
        )
        assert claude_player["options"]["model"] == "claude-3-5-sonnet"
        assert claude_player["options"]["provider"] == "anthropic"
        assert "request_params" in claude_player["options"]
        assert claude_player["options"]["request_params"]["max_tokens"] == 8192

    def test_add_player_with_params(self, tmp_path, simple_expanded_config):
        """Test add-player command with URL-like model parameters"""
        runner = CliRunner()
        config_path = tmp_path / "config.json"

        with open(config_path, "w") as f:
            json.dump(simple_expanded_config, f)

        result = runner.invoke(
            configure,
            [
                "add-player",
                str(config_path),
                "--model",
                "gpt-4o-mini?temperature=0.9&top_p=0.95",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Added player: gpt-4o-mini with params:" in result.output
        assert "temperature" in result.output
        assert "0.9" in result.output

        with open(config_path) as f:
            updated_config = json.load(f)

        # Find the new player
        new_player = next(
            p for p in updated_config["players"] if p["id"] == "gpt-4o-mini"
        )
        assert new_player["options"]["model"] == "gpt-4o-mini"
        assert new_player["options"]["provider"] == "openai"
        assert "request_params" in new_player["options"]
        assert new_player["options"]["request_params"]["temperature"] == 0.9
        assert new_player["options"]["request_params"]["top_p"] == 0.95


class TestVersionChecking:
    """Test version checking functionality in CLI"""

    def test_check_version_matching(self, simple_expanded_config):
        """Test check_version with matching versions"""

        # Add current version to config
        config = deepcopy(simple_expanded_config)
        config["xent_version"] = get_xent_version()

        # Should not raise any exception
        check_version(config, ignore_version_mismatch=False)

    def test_check_version_mismatch_raises(self, simple_expanded_config):
        """Test check_version raises SystemExit on version mismatch"""

        # Add different version to config
        config = deepcopy(simple_expanded_config)
        config["metadata"]["xent_version"] = "99.99.99"

        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            check_version(config, ignore_version_mismatch=False)
        assert exc_info.value.code == 1

    def test_check_version_mismatch_ignored(self, simple_expanded_config, caplog):
        """Test check_version with ignore flag allows mismatch"""

        # Add different version to config
        config = deepcopy(simple_expanded_config)
        config["metadata"]["xent_version"] = "99.99.99"

        # Should not raise exception when ignored
        with caplog.at_level(logging.WARNING):
            check_version(config, ignore_version_mismatch=True)

        # Should have warning in logs
        assert "mismatch" in caplog.text.lower()
        assert "99.99.99" in caplog.text
