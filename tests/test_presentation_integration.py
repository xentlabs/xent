import pytest

from xega.common.errors import XegaConfigurationError
from xega.common.x_string import XString
from xega.common.xega_types import (
    ElicitRequestEvent,
    ExpandedGameConfig,
    RevealEvent,
    XegaEvent,
    XegaGameConfig,
)
from xega.presentation.executor import PresentationFunction, get_default_presentation
from xega.runtime.default_players import DefaultXGP, MockXGP


@pytest.fixture
def game_config():
    """Create a game config with a custom presentation function"""
    presentation_code = """
def present(state, history):
    if not history:
        return "No events yet"

    lines = []
    for event in history:
        if event['type'] == 'elicit_request':
            lines.append(f"CUSTOM: {event['var_name']} requested (max {event['max_len']})")
        elif event['type'] == 'reveal':
            var_names = list(event['values'].keys())
            lines.append(f"CUSTOM: Revealed {', '.join(var_names)}")
        else:
            lines.append(f"CUSTOM: {event['type']}")

    return "\\n".join(lines)
"""

    expanded_game: ExpandedGameConfig = {
        "name": "test_game",
        "code": 'assign(x="test")\nreveal(black, x)\nelicit(black, y, 10)',
        "map_seed": "test_seed",
        "presentation_function": presentation_code,
    }

    config: XegaGameConfig = {
        "game": expanded_game,
        "players": [],
        "map_seed": "test_seed",
        "judge_model": "test",
        "npc_players": [],
        "num_variables_per_register": 4,
        "max_steps": 100,
        "auto_replay": False,
        "seed": "test",
        "num_maps_per_game": 1,
    }

    return config


class TestPresentationIntegration:
    """Test presentation layer integration with the game system"""

    def test_player_loads_custom_presentation_function(self, game_config):
        """Test that players load custom presentation functions"""
        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        assert player.presentation_function is not None
        assert callable(player.presentation_function)

    def test_custom_presentation_function_usage(self, game_config):
        """Test that custom presentation function is used when making moves"""
        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        # Simulate some events

        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(black, x)",
            "line_num": 1,
            "player": "black",
            "values": {"x": XString("test_value")},
        }

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(black, y, 10)",
            "line_num": 2,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        player.event_history = [reveal_event, elicit_event]

        # Test the presentation function directly
        result = player.presentation_function({}, player.event_history)

        assert "CUSTOM: Revealed x" in result
        assert "CUSTOM: y requested (max 10)" in result
        assert result.startswith("CUSTOM:")

    def test_presentation_function_throws_error(self, game_config):
        # Create a game config with a broken presentation function
        broken_code = """
def present(state, history):
    raise ValueError("Intentional error")
"""
        game_config["game"]["presentation_function"] = broken_code

        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        assert player.presentation_function is not None

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(black, y, 10)",
            "line_num": 1,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        player.event_history = [elicit_event]

        with pytest.raises(XegaConfigurationError):
            player.presentation_function({}, player.event_history)

    def test_default_presentation_function(self):
        """Test that the default presentation function produces expected output"""

        default_code = get_default_presentation()
        func = PresentationFunction(default_code)

        # Test with sample events
        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(black, x)",
            "line_num": 1,
            "player": "black",
            "values": {"x": XString("test_value")},
        }

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(black, y, 10)",
            "line_num": 2,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        history: list[XegaEvent] = [reveal_event, elicit_event]
        result = func({}, history)

        # Should match the format produced by event_to_message
        expected_lines = [
            "01-<reveal>: ['x: \"test_value\"']",
            "02-<elicit>: y (max 10 tokens)",
        ]

        for expected_line in expected_lines:
            assert expected_line in result

    @pytest.mark.asyncio
    async def test_full_integration_with_mock_player(self):
        """Test the full integration path with MockXGP player using presentation"""

        # Create a presentation function that includes register state info
        presentation_code = """
def present(state, history):
    lines = []

    # Include register state to verify it's being passed
    if state:
        register_values = []
        for name, value in state.items():
            # Simply try to convert to string - no hasattr needed
            try:
                register_values.append(f"{name}={str(value)[:20]}")
            except:
                pass
        if register_values:
            lines.append(f"REGISTERS: {', '.join(register_values)}")

    # Process history with custom formatting
    for event in history:
        if event['type'] == 'reveal':
            lines.append("CUSTOM_REVEAL: Values shown")
        elif event['type'] == 'elicit_request':
            lines.append(f"CUSTOM_ELICIT: Need {event['var_name']}")
        elif event['type'] == 'reward':
            lines.append("CUSTOM_REWARD: Score updated")

    if not lines:
        lines.append("CUSTOM_START: Game beginning")

    return "\\n".join(lines)
"""

        # Create game configuration
        expanded_game: ExpandedGameConfig = {
            "name": "test_integration",
            "code": """assign(x="initial_value")
reveal(black, x)
elicit(black, z, 10)""",
            "map_seed": "test_seed",
            "presentation_function": presentation_code,
        }

        config: XegaGameConfig = {
            "game": expanded_game,
            "players": [
                {
                    "name": "black",
                    "id": "mock_id",
                    "player_type": "mock",
                    "options": {},
                }
            ],
            "map_seed": "test_seed",
            "judge_model": "test",
            "npc_players": [],
            "num_variables_per_register": 4,
            "max_steps": 100,
            "auto_replay": False,
            "seed": "test",
            "num_maps_per_game": 1,
        }

        # Create MockXGP player with the game config
        mock_player = MockXGP("black", "mock_id", None, config)

        # Simulate reveal event
        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(black, x)",
            "line_num": 2,
            "player": "black",
            "values": {"x": XString("initial_value")},
        }
        await mock_player.post(reveal_event)

        # Simulate elicit request event
        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(black, z, 10)",
            "line_num": 3,
            "player": "black",
            "var_name": "z",
            "max_len": 10,
            "registers": {},
        }
        await mock_player.post(elicit_event)

        # Create register states with actual values to verify they're passed
        register_states = {
            "x": XString("initial_value"),
            "y": XString("another_value"),
            "empty": XString(""),
        }

        # Call make_move - this is the crucial integration point
        move, tokens = await mock_player.make_move("z", register_states)

        # Verify the move was made
        assert move == "mocked_move"

        # Verify presentation function was used in make_move
        assert mock_player.last_message_to_llm is not None
        message = mock_player.last_message_to_llm

        # Check for custom presentation markers
        assert "CUSTOM_" in message, f"Custom presentation not found in: {message}"
        assert "CUSTOM_REVEAL" in message
        assert "CUSTOM_ELICIT" in message

        # Verify registers were passed (non-empty state)
        assert "REGISTERS:" in message, "Register state not passed to presentation"
        assert "x=" in message, "Register x not in presentation output"
        assert "y=" in message, "Register y not in presentation output"

        # Verify default formatting is NOT present
        assert "02-<reveal>" not in message, "Default formatting should not be present"
        assert "03-<elicit>" not in message, "Default formatting should not be present"

    @pytest.mark.asyncio
    async def test_presentation_throws_with_mock_player(self):
        """Test that MockXGP falls back to default formatting when presentation fails"""

        # Create a broken presentation function
        broken_presentation = """
def present(state, history):
    # Intentionally cause an error to test fallback
    return 1 / 0  # Division by zero error
"""

        expanded_game: ExpandedGameConfig = {
            "name": "test_fallback",
            "code": """reveal(black, "test")
elicit(black, x, 5)""",
            "map_seed": "test_seed",
            "presentation_function": broken_presentation,
        }

        config: XegaGameConfig = {
            "game": expanded_game,
            "players": [
                {"name": "black", "id": "mock_id", "player_type": "mock", "options": {}}
            ],
            "map_seed": "test_seed",
            "judge_model": "test",
            "npc_players": [],
            "num_variables_per_register": 4,
            "max_steps": 100,
            "auto_replay": False,
            "seed": "test",
            "num_maps_per_game": 1,
        }

        mock_player = MockXGP("black", "mock_id", None, config)

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(black, x, 5)",
            "line_num": 2,
            "player": "black",
            "var_name": "x",
            "max_len": 5,
            "registers": {},
        }

        await mock_player.post(elicit_event)

        register_states = {"test": XString("test_value")}
        with pytest.raises(XegaConfigurationError):
            move, tokens = await mock_player.make_move("x", register_states)
