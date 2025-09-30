import logging
from collections.abc import Callable, Mapping
from typing import Any

from xent.common.configuration_types import XentEvent, XentMetadata
from xent.common.errors import XentConfigurationError, XentInternalError
from xent.common.x_list import XList
from xent.common.x_string import XString

DEFAULT_PRESENTATION = '''
from xent.presentation.sdk import (
    format_elicit_request,
    format_elicit_response,
    format_reveal,
    format_reward,
    format_failed_ensure,
)

def present(state, history, metadata):
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
            formatted, _ = format_reward(event)
            output.append(formatted)
        elif event['type'] == 'failed_ensure':
            output.append(format_failed_ensure(event))
        else:
            # Fallback for unknown event types
            output.append(f"Unknown event: {event}")
    return '\\n'.join(output)
'''

SAMPLE_METADATA: XentMetadata = XentMetadata(
    benchmark_id="bid",
    xent_version="0.1.0",
    judge_model="judge",
    num_rounds_per_game=2,
    seed="seed",
    store_full_player_interactions=False,
)

SINGLE_PRESENTATION = '''
def present(state, history, metadata):
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
        self.present_func: (
            Callable[[Mapping[str, Any], list[XentEvent], XentMetadata], str] | None
        ) = None

        try:
            self.compiled_code = compile(code_string, "<presentation>", "exec")
        except SyntaxError as e:
            raise XentInternalError(f"Presentation function syntax error: {e}") from e

        # Allow full Python imports - presentations are trusted code
        self.namespace: Any = {}

        try:
            exec(self.compiled_code, self.namespace)
        except Exception as e:
            raise XentConfigurationError(
                f"Error executing presentation function: {e}"
            ) from e

        if "present" not in self.namespace:
            raise XentConfigurationError(
                "Presentation function must define a 'present' function"
            )

        present_func = self.namespace["present"]
        if not callable(present_func):
            raise XentInternalError("'present' must be a callable function")

        # Type narrowing - we know it's callable now
        self.present_func = present_func

    def __call__(
        self,
        state: Mapping[str, XString | XList],
        history: list[XentEvent],
        metadata: XentMetadata,
    ) -> str:
        if self.present_func is None:
            raise XentInternalError("Presentation function not properly initialized")

        try:
            result = self.present_func(state, history, metadata)
            if not isinstance(result, str):
                logging.warning(
                    f"Presentation function returned non-string: {type(result)}. Converting to string."
                )
                return str(result)
            return result
        except Exception as e:
            logging.error(f"Error in presentation function execution: {e}")
            raise XentConfigurationError(
                "Error in presentation function execution"
            ) from e

    def validate(
        self,
        sample_state: dict[str, Any] | None = None,
        sample_history: list[XentEvent] | None = None,
        sample_metadata: XentMetadata | None = None,
    ) -> bool:
        if sample_state is None:
            sample_state = {}
        if sample_history is None:
            sample_history = []
        if sample_metadata is None:
            sample_metadata = SAMPLE_METADATA

        try:
            result = self(sample_state, sample_history, sample_metadata)
            return isinstance(result, str)
        except Exception as e:
            logging.error(f"Presentation function validation failed: {e}")
            return False
