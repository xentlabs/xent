from typing import Dict, List, Literal, Optional, TypedDict, Union

from xega.common.token_xent_list import TokenXentList


class BaseEvent(TypedDict):
    line: str
    line_num: int
    player: str


class ElicitRequestEvent(BaseEvent):
    type: Literal["elicit_request"]
    var_name: str
    max_len: int


class ElicitResponseEvent(BaseEvent):
    type: Literal["elicit_response"]
    response: str


class RevealEvent(BaseEvent):
    type: Literal["reveal"]
    values: List[str]


class RewardEvent(BaseEvent):
    type: Literal["reward"]
    value: TokenXentList


class FailedEnsureEvent(BaseEvent):
    type: Literal["failed_ensure"]
    ensure_results: List[bool]
    beacon: str


XegaEvent = Union[
    ElicitRequestEvent, ElicitResponseEvent, RevealEvent, RewardEvent, FailedEnsureEvent
]

LLMRole = Literal["user", "assistant", "system"]


class LLMMessage(TypedDict):
    role: LLMRole
    content: str


PlayerName = Literal["black", "white", "alice", "bob", "carol", "env"]
PlayerType = Literal["default", "human", "mock"]
PlayerOptions = Dict[str, Union[str, int, float, bool]]


class PlayerConfig(TypedDict):
    name: PlayerName
    id: str
    player_type: PlayerType
    options: Optional[PlayerOptions]


class GameConfig(TypedDict):
    name: str
    code: str


class XegaMetadata(TypedDict):
    judge_model: str
    npc_players: List[PlayerConfig]
    num_variables_per_register: int
    max_steps: int
    auto_replay: bool
    seed: str
    num_maps_per_game: int


class XegaBenchmarkConfig(XegaMetadata):
    games: List[GameConfig]
    players: List[List[PlayerConfig]]  # List of player configurations for each game
    benchmark_id: str


class XegaGameConfig(XegaMetadata):
    game: GameConfig
    players: List[PlayerConfig]
    map_seed: str


class XegaGameIterationResult(TypedDict):
    scores: Dict[PlayerName, float]
    xrt_history: List[XegaEvent]


class XegaGameResult(TypedDict):
    game: XegaGameConfig
    game_results: List[XegaGameIterationResult]
    scores: Dict[PlayerName, float]


class XegaBenchmarkResult(TypedDict):
    config: XegaBenchmarkConfig
    game_results: List[XegaGameResult]
