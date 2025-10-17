# Event types
from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict

from xent.common.token_xent_list import TokenXentList
from xent.common.x_list import XList
from xent.common.x_string import XString

LLMRole = Literal["user", "assistant", "system"]


class LLMMessage(TypedDict):
    role: LLMRole
    content: str


class TokenUsage(TypedDict):
    input_tokens: int
    output_tokens: int


class BaseXentEvent(TypedDict):
    line: str
    line_num: int
    player: str


class ElicitRequestEvent(BaseXentEvent):
    type: Literal["elicit_request"]
    var_name: str
    max_len: int
    registers: Mapping[str, XString | XList]


class ElicitResponseEvent(BaseXentEvent):
    type: Literal["elicit_response"]
    response: str
    token_usage: TokenUsage
    prompts: NotRequired[list[LLMMessage]]
    full_response: NotRequired[list[LLMMessage]]


class RevealEvent(BaseXentEvent):
    type: Literal["reveal"]
    # Map of variable names to their values.
    values: Mapping[str, XString | XList]


class RewardEvent(BaseXentEvent):
    type: Literal["reward"]
    value: TokenXentList


class FailedEnsureEvent(BaseXentEvent):
    type: Literal["failed_ensure"]
    ensure_results: list[bool]
    beacon: str


class RoundStartedEvent(BaseXentEvent):
    type: Literal["round_started"]
    round_index: int


class RoundFinishedEvent(BaseXentEvent):
    type: Literal["round_finished"]
    round_index: int


XentEvent = (
    ElicitRequestEvent
    | ElicitResponseEvent
    | RevealEvent
    | RewardEvent
    | FailedEnsureEvent
    | RoundStartedEvent
    | RoundFinishedEvent
)


def serialize_event(event: XentEvent) -> dict[str, Any]:
    match event["type"]:
        case "elicit_request":
            return {
                **event,
                "registers": {k: v.serialize() for k, v in event["registers"].items()},
            }

        case "elicit_response":
            return {
                **event,
                "token_usage": dict(event["token_usage"]),
            }

        case "reveal":
            return {
                **event,
                "values": {k: v.serialize() for k, v in event["values"].items()},
            }

        case "reward":
            return {
                **event,
                "value": event["value"].serialize(),
            }

        case _:
            return dict(event)


def deserialize_event(payload: Mapping[str, Any]) -> XentEvent:
    def _val(d: dict[str, Any]):
        tag = d["type"]
        if tag == "XString":
            return XString.deserialize(d)
        elif tag == "XList":
            return XList.deserialize(d)  # adjust if your API differs

    match payload["type"]:
        case "elicit_request":
            return {
                **payload,
                "registers": {k: _val(v) for k, v in payload["registers"].items()},
            }  # type: ignore[return-value]

        case "elicit_response":
            tu = payload["token_usage"]
            return {
                **payload,
                "token_usage": {
                    "input_tokens": int(tu["input_tokens"]),
                    "output_tokens": int(tu["output_tokens"]),
                },
            }  # type: ignore[return-value]

        case "reveal":
            return {
                **payload,
                "values": {k: _val(v) for k, v in payload["values"].items()},
            }  # type: ignore[return-value]

        case "reward":
            return {
                **payload,
                "value": TokenXentList.deserialize(payload["value"]),
            }  # type: ignore[return-value]

        case _:
            # "failed_ensure", "round_started", "round_finished", etc. pass through.
            return dict(payload)  # type: ignore[return-value]
