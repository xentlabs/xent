# Event types
from typing import Literal, TypedDict

from xega.common.configuration_types import TokenUsage
from xega.common.token_xent_list import TokenXentList
from xega.common.x_string import XString


class BaseXegaEvent(TypedDict):
    line: str
    line_num: int
    player: str


class ElicitRequestEvent(BaseXegaEvent):
    type: Literal["elicit_request"]
    var_name: str
    max_len: int
    registers: dict[str, XString]


class ElicitResponseEvent(BaseXegaEvent):
    type: Literal["elicit_response"]
    response: str
    token_usage: TokenUsage


class RevealEvent(BaseXegaEvent):
    type: Literal["reveal"]
    # Map of variable names to their values.
    values: dict[str, XString]


class RewardEvent(BaseXegaEvent):
    type: Literal["reward"]
    value: TokenXentList


class FailedEnsureEvent(BaseXegaEvent):
    type: Literal["failed_ensure"]
    ensure_results: list[bool]
    beacon: str


XegaEvent = (
    ElicitRequestEvent
    | ElicitResponseEvent
    | RevealEvent
    | RewardEvent
    | FailedEnsureEvent
)
