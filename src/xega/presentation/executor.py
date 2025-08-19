import logging
from collections.abc import Callable
from typing import Any

from xega.common.errors import XegaConfigurationError, XegaInternalError
from xega.common.xega_types import XegaEvent
from xega.presentation import sdk

DEFAULT_PRESENTATION = '''
def present(state, history):
    """Default presentation matching current system output"""
    output = []
    for event in history:
        if event['type'] == 'elicit_request':
            output.append(format_elicit_request(event))
        elif event['type'] == 'elicit_response':
            output.append(format_elicit_response(event))
        elif event['type'] == 'reveal':
            output.append(format_reveal(event))
        elif event['type'] == 'reward':
            output.append(format_reward(event))
        elif event['type'] == 'failed_ensure':
            output.append(format_failed_ensure(event))
        else:
            # Fallback for unknown event types
            output.append(f"Unknown event: {event}")
    return '\\n'.join(output)
'''

SINGLE_PRESENTATION = '''
def present(state, history):
    story = state["s"]
    game_overview = f"""I am going to give you a short text. Your job is to provide a string that will prefix that text. Your goal is to minimize the cross-entropy of the text given the prefix you provide. You should respond with what will make the text as likely as possible.

The text is: "{story}"

Your response will be used as the prefix to that text and you will be scored on how well it helps predict that text. You may not use any words from the text in your response, regardless of case or punctuation. You can only use a maximum of 10 tokens for your prefix."""
    previous_attempts = []

    for event in history:
        if event["type"] == "elicit_response":
            previous_attempts.append("<attempt>")
            previous_attempts.append("You provided: " + event["response"])
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 2)
            previous_attempts.append(f"Total score for that response: {score}")
            previous_attempts.append(
                f"Per token score for that response: {str(event['value'])}"
            )
            previous_attempts.append("</attempt>")

    if len(previous_attempts) == 0:
        instructions = "Provide your prefix inside of `<move></move>` tags. Any other text in your response will be ignored. You will be given feedback on your prefix and a chance to improve your prefix."
        output = [game_overview, "", instructions]
    else:
        instructions = "Use your previous attempts above to further optimize your prefix. Provide your prefix inside of `<move></move>` tags. Any other text in your response will be ignored."
        output = (
            [game_overview, "", "<previousAttempts>"]
            + previous_attempts
            + ["</previousAttempts>", "", instructions]
        )

    return "\\n".join(output)
'''


def get_default_presentation() -> str:
    return DEFAULT_PRESENTATION.strip()


def get_single_presentation() -> str:
    return SINGLE_PRESENTATION.strip()


class PresentationFunction:
    def __init__(self, code_string: str):
        self.code_string = code_string
        self.compiled_code = None
        self.present_func: Callable[[dict[str, Any], list[XegaEvent]], str] | None = (
            None
        )

        try:
            self.compiled_code = compile(code_string, "<presentation>", "exec")
        except SyntaxError as e:
            raise XegaInternalError(f"Presentation function syntax error: {e}") from e

        self.namespace = {
            "__builtins__": {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "min": min,
                "max": max,
                "sum": sum,
                "sorted": sorted,
                "reversed": reversed,
                "any": any,
                "all": all,
                "abs": abs,
                "round": round,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
            },
            # SDK functions available to presentation code
            "format_reveal": sdk.format_reveal,
            "format_elicit_request": sdk.format_elicit_request,
            "format_elicit_response": sdk.format_elicit_response,
            "format_reward": sdk.format_reward,
            "format_failed_ensure": sdk.format_failed_ensure,
            "get_event_summary": sdk.get_event_summary,
            "get_current_registers": sdk.get_current_registers,
            "format_registers_display": sdk.format_registers_display,
        }

        try:
            exec(self.compiled_code, self.namespace)
        except Exception as e:
            raise XegaConfigurationError(
                f"Error executing presentation function: {e}"
            ) from e

        if "present" not in self.namespace:
            raise XegaConfigurationError(
                "Presentation function must define a 'present' function"
            )

        present_func = self.namespace["present"]
        if not callable(present_func):
            raise XegaInternalError("'present' must be a callable function")

        # Type narrowing - we know it's callable now
        self.present_func = present_func

    def __call__(self, state: dict[str, Any], history: list[XegaEvent]) -> str:
        if self.present_func is None:
            raise XegaInternalError("Presentation function not properly initialized")

        try:
            result = self.present_func(state, history)
            if not isinstance(result, str):
                logging.warning(
                    f"Presentation function returned non-string: {type(result)}. Converting to string."
                )
                return str(result)
            return result
        except Exception as e:
            logging.error(f"Error in presentation function execution: {e}")
            raise XegaConfigurationError(
                "Error in presentation function execution"
            ) from e

    def validate(
        self,
        sample_state: dict[str, Any] | None = None,
        sample_history: list[XegaEvent] | None = None,
    ) -> bool:
        if sample_state is None:
            sample_state = {}
        if sample_history is None:
            sample_history = []

        try:
            result = self(sample_state, sample_history)
            return isinstance(result, str)
        except Exception as e:
            logging.error(f"Presentation function validation failed: {e}")
            return False
