from typing import Any, Literal, NotRequired, TypedDict, TypeGuard

from xent.common.xent_event import TokenUsage, XentEvent

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


# TODO later dynamically register text generators
TextGeneratorType = Literal["JUDGE", "COMMUNITY_ARCHIVE"]


class TextGenerationConfig(TypedDict):
    generator_type: TextGeneratorType
    generator_config: dict[str, Any]
    max_length: int


class ExpansionConfig(TypedDict):
    num_maps_per_game: int
    text_generation_config: TextGenerationConfig


class XentMetadata(TypedDict):
    benchmark_id: str
    xent_version: str
    judge_model: str
    num_rounds_per_game: int
    seed: str
    store_full_player_interactions: NotRequired[bool]
    npcs: NotRequired[list[PlayerConfig]]


class CondensedXentBenchmarkConfig(TypedDict):
    config_type: Literal["condensed_xent_config"]
    metadata: XentMetadata
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


class ExpandedXentBenchmarkConfig(TypedDict):
    config_type: Literal["expanded_xent_config"]
    metadata: XentMetadata
    players: list[PlayerConfig]
    games: list[GameConfig]
    maps: list[GameMapConfig]


# Execution definitions


# Executable Game is the smallest work unit we currently support. It completes or fails
# atomically - you can't have a result that is partially finished.
class ExecutableGameMap(TypedDict):
    game_map: GameMapConfig
    metadata: XentMetadata
    player: PlayerConfig


# Result definitions


class GameMapRoundResult(TypedDict):
    score: float
    token_usage: TokenUsage
    history: list[XentEvent]


class GameMapResults(TypedDict):
    game_map: GameMapConfig
    metadata: XentMetadata
    player: PlayerConfig
    score: float
    token_usage: TokenUsage
    round_results: list[GameMapRoundResult]


class BenchmarkResult(TypedDict):
    expanded_config: ExpandedXentBenchmarkConfig
    results: list[GameMapResults]
