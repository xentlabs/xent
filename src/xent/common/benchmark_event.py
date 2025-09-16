from datetime import datetime
from typing import Literal, TypedDict

from xent.common.configuration_types import (
    BenchmarkResult,
    ExecutableGameMap,
    GameMapResults,
)


class BaseBenchmarkEvent(TypedDict):
    timestamp: datetime
    benchmark_id: str


class BenchmarkStartedEvent(BaseBenchmarkEvent):
    type: Literal["benchmark_started"]


class BenchmarkFinishedEvent(BaseBenchmarkEvent):
    type: Literal["benchmark_finished"]
    results: BenchmarkResult


class GameMapStartedEvent(BaseBenchmarkEvent):
    type: Literal["game_map_started"]
    game_map: ExecutableGameMap


class GameMapFinishedEvent(BaseBenchmarkEvent):
    type: Literal["game_map_finished"]
    results: GameMapResults


BenchmarkEvent = (
    BenchmarkStartedEvent
    | BenchmarkFinishedEvent
    | GameMapStartedEvent
    | GameMapFinishedEvent
)
