# Event types
from typing import Literal, TypedDict

from xega.common.token_xent_list import TokenXentList
from xega.common.x_string import XString


class TokenUsage(TypedDict):
    input_tokens: int
    output_tokens: int


class BaseXegaEvent(TypedDict):
    pass


class LineXegaEvent(BaseXegaEvent):
    line: str
    line_num: int
    player: str


class ElicitRequestEvent(LineXegaEvent):
    type: Literal["elicit_request"]
    var_name: str
    max_len: int
    registers: dict[str, XString]


class ElicitResponseEvent(LineXegaEvent):
    type: Literal["elicit_response"]
    response: str
    token_usage: TokenUsage


class RevealEvent(LineXegaEvent):
    type: Literal["reveal"]
    # Map of variable names to their values.
    values: dict[str, XString]


class RewardEvent(LineXegaEvent):
    type: Literal["reward"]
    value: TokenXentList


class FailedEnsureEvent(LineXegaEvent):
    type: Literal["failed_ensure"]
    ensure_results: list[bool]
    beacon: str


class RoundStartedEvent(BaseXegaEvent):
    type: Literal["round_started"]
    round_index: int


class RoundFinishedEvent(BaseXegaEvent):
    type: Literal["round_finished"]
    round_index: int
    best_score: float


XegaEvent = (
    ElicitRequestEvent
    | ElicitResponseEvent
    | RevealEvent
    | RewardEvent
    | FailedEnsureEvent
    | RoundStartedEvent
    | RoundFinishedEvent
)
