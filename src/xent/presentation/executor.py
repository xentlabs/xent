import logging
from collections.abc import Callable, Mapping
from typing import Any

from xent.common.configuration_types import XentEvent, XentMetadata
from xent.common.errors import XentConfigurationError, XentInternalError
from xent.common.version import get_xent_version
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import LLMMessage

# A default example for presentation
DEFAULT_PRESENTATION = """
from typing import Any
from xent.presentation.sdk import (
    ChatBuilder,
    format_elicit_request,
    format_elicit_response,
    format_reveal,
    format_reward,
    format_failed_ensure,
)

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    b = ChatBuilder()

    # Send a one-time introduction/instructions
    if not ctx.get('intro_sent', False):
        b.user(
            "You are playing a text game. Provide your move inside <move></move> tags. Any other text will be ignored."
        )
        ctx['intro_sent'] = True

    # Summarize what happened since the last elicit
    for event in since_events:
        t = event.get('type')
        if t == 'elicit_request':
            b.user(format_elicit_request(event))
        elif t == 'elicit_response':
            b.user(format_elicit_response(event))
        elif t == 'reveal':
            b.user(format_reveal(event))
        elif t == 'reward':
            formatted, _ = format_reward(event)
            b.user("Score update:\\n" + str(formatted))
        elif t == 'failed_ensure':
            b.user(format_failed_ensure(event))
        else:
            b.user("Event: " + str(event))

    # Close with a concise instruction cue
    b.user("Now provide your next move inside <move></move> tags.")

    return b.render(), ctx
"""


SAMPLE_METADATA: XentMetadata = XentMetadata(
    benchmark_id="bid",
    xent_version=get_xent_version(),
    judge_model="judge",
    num_rounds_per_game=2,
    seed="seed",
    store_full_player_interactions=False,
    npcs=[],
)


def get_default_presentation() -> str:
    return DEFAULT_PRESENTATION.strip()


class PresentationFunction:
    """
    Loader/executor for presentation functions that implement:

        present_turn(state, since_events, metadata, full_history=None, ctx=None)
            -> list[LLMMessage] | tuple[list[LLMMessage], dict[str, Any]]

    The __call__ normalizes the return into (messages, new_ctx).
    """

    def __init__(self, code_string: str):
        self.code_string = code_string
        self.compiled_code = None
        self.present_turn_func: (
            Callable[
                [
                    Mapping[str, Any],
                    list[XentEvent],
                    XentMetadata,
                    list[XentEvent] | None,
                    dict[str, Any] | None,
                ],
                Any,
            ]
            | None
        ) = None

        try:
            self.compiled_code = compile(code_string, "<presentation_turn>", "exec")
        except SyntaxError as e:
            raise XentInternalError(
                f"Turn presentation function syntax error: {e}"
            ) from e

        self.namespace: Any = {}

        try:
            exec(self.compiled_code, self.namespace)
        except Exception as e:
            raise XentConfigurationError(
                f"Error executing turn presentation function: {e}"
            ) from e

        if "present_turn" not in self.namespace:
            raise XentConfigurationError(
                "Turn presentation must define a 'present_turn' function"
            )

        present_turn_func = self.namespace["present_turn"]
        if not callable(present_turn_func):
            raise XentInternalError("'present_turn' must be a callable function")

        self.present_turn_func = present_turn_func  # type: ignore

    def __call__(
        self,
        state: Mapping[str, XString | XList],
        since_events: list[XentEvent],
        metadata: XentMetadata,
        full_history: list[XentEvent] | None = None,
        ctx: dict[str, Any] | None = None,
    ) -> tuple[list[LLMMessage], dict[str, Any]]:
        if self.present_turn_func is None:
            raise XentInternalError(
                "Turn presentation function not properly initialized"
            )

        try:
            result = self.present_turn_func(
                state, since_events, metadata, full_history, ctx
            )
            # Accept either list[LLMMessage] or (list[LLMMessage], ctx)
            messages: list[LLMMessage]
            new_ctx: dict[str, Any]

            if isinstance(result, tuple) and len(result) == 2:
                messages_candidate, ctx_candidate = result
                messages = (
                    list(messages_candidate) if messages_candidate is not None else []
                )
                new_ctx = (
                    dict(ctx_candidate)
                    if isinstance(ctx_candidate, dict)
                    else (ctx or {})
                )
            else:
                messages = list(result) if result is not None else []
                new_ctx = ctx or {}

            # Coerce message shapes to LLMMessage
            normalized: list[LLMMessage] = []
            for m in messages:
                role = getattr(m, "role", None) or (
                    m.get("role") if isinstance(m, dict) else None
                )
                content = getattr(m, "content", None) or (
                    m.get("content") if isinstance(m, dict) else None
                )
                if not role or not content:
                    logging.warning(f"Invalid message in turn presentation output: {m}")
                    continue
                normalized.append({"role": str(role), "content": str(content)})  # type: ignore[typeddict-item]

            return normalized, new_ctx
        except Exception as e:
            logging.error(f"Error in turn presentation function execution: {e}")
            raise XentConfigurationError(
                "Error in turn presentation function execution"
            ) from e

    def validate(
        self,
        sample_state: dict[str, Any] | None = None,
        sample_since_events: list[XentEvent] | None = None,
        sample_metadata: XentMetadata | None = None,
    ) -> bool:
        if sample_state is None:
            sample_state = {}
        if sample_since_events is None:
            sample_since_events = []
        if sample_metadata is None:
            sample_metadata = SAMPLE_METADATA

        try:
            messages, _ctx = self(sample_state, sample_since_events, sample_metadata)
            valid = isinstance(messages, list)
            return valid
        except Exception as e:
            logging.error(f"Presentation function validation failed: {e}")
            return False
