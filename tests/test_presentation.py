import pytest

from xega.common.errors import XegaConfigurationError, XegaInternalError
from xega.common.token_xent_list import TokenXentList
from xega.common.x_string import XString
from xega.common.xega_types import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    RevealEvent,
    RewardEvent,
    XegaEvent,
)
from xega.presentation.executor import PresentationFunction
from xega.presentation.sdk import (
    format_elicit_request,
    format_elicit_response,
    format_failed_ensure,
    format_registers_display,
    format_reveal,
    format_reward,
    get_current_registers,
    get_event_summary,
)


class TestSDKFunctions:
    def test_format_elicit_request(self):
        event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(player, var, 10)",
            "line_num": 5,
            "player": "alice",
            "var_name": "move",
            "max_len": 10,
            "registers": {},
        }
        result = format_elicit_request(event)
        assert result == "05-<elicit>: move (max 10 tokens)"

    def test_format_elicit_response(self):
        event: ElicitResponseEvent = {
            "type": "elicit_response",
            "line": "elicit(player, var, 10)",
            "line_num": 5,
            "player": "alice",
            "response": "my move",
            "token_usage": {"input_tokens": 10, "output_tokens": 5},
        }
        result = format_elicit_response(event)
        assert result == "05-<elicit response>: my move"

    def test_format_reveal(self):
        values = {"var1": XString("value1"), "var2": XString("value2")}
        event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(player, var1, var2)",
            "line_num": 3,
            "player": "alice",
            "values": values,
        }
        result = format_reveal(event)
        expected = "03-<reveal>: ['var1: \"value1\"', 'var2: \"value2\"']"
        assert result == expected

    def test_format_reward(self):
        reward_value = TokenXentList([("token1", 1.5), ("token2", 0.5)])
        event: RewardEvent = {
            "type": "reward",
            "line": "reward(player, score)",
            "line_num": 8,
            "player": "alice",
            "value": reward_value,
        }
        result = format_reward(event)
        assert "08-<reward>:" in result
        assert "Total reward:" in result

    def test_format_failed_ensure(self):
        event: FailedEnsureEvent = {
            "type": "failed_ensure",
            "line": "ensure(condition)",
            "line_num": 10,
            "player": "alice",
            "ensure_results": [True, False, True],
            "beacon": "previous_elicit",
        }
        result = format_failed_ensure(event)
        expected = "10-<ensure>: Failed ensure. Argument 0 result: True, Argument 1 result: False, Argument 2 result: True. Moving code execution to beacon: previous_elicit"
        assert result == expected

    def test_get_event_summary(self):
        events: list[XegaEvent] = [
            {
                "type": "elicit_request",
                "line": "",
                "line_num": 1,
                "player": "alice",
                "var_name": "move",
                "max_len": 10,
                "registers": {},
            },
            {
                "type": "elicit_response",
                "line": "",
                "line_num": 1,
                "player": "alice",
                "response": "test",
                "token_usage": {"input_tokens": 1, "output_tokens": 1},
            },
            {
                "type": "elicit_request",
                "line": "",
                "line_num": 2,
                "player": "alice",
                "var_name": "move2",
                "max_len": 5,
                "registers": {},
            },
        ]
        result = get_event_summary(events)
        assert "Game history:" in result
        assert "2 elicit_request" in result
        assert "1 elicit_response" in result

    def test_get_current_registers(self):
        state = {
            "var1": XString("value1"),
            "var2": "string_value",
            "var3": 42,
            "var4": True,
            "var5": {"not": "extractable"},
        }

        registers = get_current_registers(state)
        assert registers["var1"] == "value1"
        assert registers["var2"] == "string_value"
        assert registers["var3"] == "42"
        assert registers["var4"] == "True"
        assert "var5" not in registers

    def test_format_registers_display(self):
        registers = {"var1": "value1", "var2": "value2"}
        result = format_registers_display(registers)
        assert "Current registers:" in result
        assert "var1: value1" in result
        assert "var2: value2" in result

        empty_result = format_registers_display({})
        assert empty_result == "No registers available"


class TestPresentationFunction:
    def test_simple_presentation_function(self):
        code = """
def present(state, history):
    return "Simple presentation"
"""
        func = PresentationFunction(code)
        result = func({}, [])
        assert result == "Simple presentation"

    def test_presentation_with_sdk_functions(self):
        code = """
def present(state, history):
    if not history:
        return "No events yet"

    lines = []
    for event in history:
        if event['type'] == 'elicit_request':
            lines.append(format_elicit_request(event))
        elif event['type'] == 'reveal':
            lines.append(format_reveal(event))

    return "\\n".join(lines)
"""
        func = PresentationFunction(code)

        events: list[XegaEvent] = [
            {
                "type": "elicit_request",
                "line": "test",
                "line_num": 1,
                "player": "alice",
                "var_name": "move",
                "max_len": 10,
                "registers": {},
            }
        ]

        result = func({}, events)
        assert "01-<elicit>: move (max 10 tokens)" in result

    def test_presentation_function_validation(self):
        valid_code = """
def present(state, history):
    return "Valid function"
"""
        func = PresentationFunction(valid_code)
        assert func.validate()

    def test_invalid_syntax(self):
        with pytest.raises(XegaInternalError):
            PresentationFunction("def present(state history):")  # Missing comma

    def test_missing_present_function(self):
        with pytest.raises(XegaConfigurationError):
            PresentationFunction("def other_function(): pass")

    def test_non_callable_present(self):
        with pytest.raises(XegaInternalError):
            PresentationFunction("present = 'not a function'")
