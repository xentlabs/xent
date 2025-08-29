from typing import Literal, TypedDict, TypeGuard

from xega.common.xega_event import TokenUsage, XegaEvent

PlayerName = Literal["black", "white", "alice", "bob", "carol", "env"]
OmniscientPlayerName = Literal["black", "white", "env"]


def is_omniscient_player_name(value: str) -> TypeGuard[OmniscientPlayerName]:
    return value in ("black", "white", "env")


PlayerOptions = dict[str, str | int | float | bool]


class PlayerConfig(TypedDict):
    name: PlayerName
    id: str
    player_type: str
    options: PlayerOptions | None


class GameConfig(TypedDict):
    name: str
    code: str
    presentation_function: str


# Condensed configuration definitions


class ExpansionConfig(TypedDict):
    num_maps_per_game: int


class XegaMetadata(TypedDict):
    benchmark_id: str
    xega_version: str
    judge_model: str
    num_rounds_per_game: int
    seed: str


class CondensedXegaBenchmarkConfig(TypedDict):
    config_type: Literal["condensed_xega_config"]
    metadata: XegaMetadata
    expansion_config: ExpansionConfig
    players: list[PlayerConfig]
    games: list[GameConfig]


# Expanded configuration


# GameMapConfig code should never contain `story` calls or any other preprocessing calls
class GameMapConfig(TypedDict):
    name: str
    code: str
    presentation_function: str
    map_seed: str


class ExpandedXegaBenchmarkConfig(TypedDict):
    config_type: Literal["expanded_xega_config"]
    metadata: XegaMetadata
    players: list[PlayerConfig]
    games: list[GameConfig]
    maps: list[GameMapConfig]


# Execution definitions


# Executable Game is the smallest work unit we currently support. It completes or fails
# atomically - you can't have a result that is partially finished.
class ExecutableGameMap(TypedDict):
    game_map: GameMapConfig
    metadata: XegaMetadata
    player: PlayerConfig


# Result definitions


class GameMapRoundResult(TypedDict):
    score: float
    token_usage: TokenUsage
    history: list[XegaEvent]


class GameMapResults(TypedDict):
    game_map: GameMapConfig
    metadata: XegaMetadata
    player: PlayerConfig
    score: float
    token_usage: TokenUsage
    round_results: list[GameMapRoundResult]


class BenchmarkResult(TypedDict):
    expanded_config: ExpandedXegaBenchmarkConfig
    results: list[GameMapResults]
