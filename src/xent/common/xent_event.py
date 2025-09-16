# Event types
from typing import Literal, TypedDict

from xent.common.token_xent_list import TokenXentList
from xent.common.x_string import XString


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
    registers: dict[str, XString]


class ElicitResponseEvent(BaseXentEvent):
    type: Literal["elicit_response"]
    response: str
    token_usage: TokenUsage


class RevealEvent(BaseXentEvent):
    type: Literal["reveal"]
    # Map of variable names to their values.
    values: dict[str, XString]


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
