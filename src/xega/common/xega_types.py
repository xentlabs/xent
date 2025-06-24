from typing import Dict, List, Literal, Optional, TypedDict, Union

from xega.common.token_xent_list import TokenXentList

# Event types


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

# Configuration types. These are input to the Xega system to define benchmarks.

PlayerName = Literal["black", "white", "alice", "bob", "carol", "env"]
PlayerOptions = Dict[str, Union[str, int, float, bool]]


class PlayerConfig(TypedDict):
    name: PlayerName
    id: str
    player_type: str
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
    config_type: Literal["short_benchmark_config"]
    games: List[GameConfig]
    players: List[List[PlayerConfig]]  # List of player configurations for each game
    benchmark_id: str


# Execution types. These are unrolled configuration objects that fully specify the benchmark.


# The `code` field in `ExpandedGameConfig` is the fully expanded game code.
# Specifically, it doesn't contain any "story()" calls - those are preprocessed to
# be replaced with string literals.
class ExpandedGameConfig(TypedDict):
    name: str
    code: str
    map_seed: str


class XegaGameConfig(XegaMetadata):
    game: ExpandedGameConfig
    players: List[PlayerConfig]
    map_seed: str


# `ExpandedXegaBenchmarkConfig` defines the complete set of
# independent work units that make up the benchmark.
class ExpandedXegaBenchmarkConfig(XegaMetadata):
    config_type: Literal["expanded_benchmark_config"]
    games: List[XegaGameConfig]
    benchmark_id: str


# Result types


class XegaGameIterationResult(TypedDict):
    scores: Dict[PlayerName, float]
    xrt_history: List[XegaEvent]


class XegaGameResult(TypedDict):
    game: XegaGameConfig
    game_results: List[XegaGameIterationResult]
    scores: Dict[PlayerName, float]


class XegaBenchmarkResult(TypedDict):
    config: ExpandedXegaBenchmarkConfig
    game_results: List[XegaGameResult]
