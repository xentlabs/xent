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


def get_default_presentation() -> str:
    """
    Get the default presentation function code.

    Returns:
        String containing the default presentation function
    """
    return DEFAULT_PRESENTATION.strip()


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
