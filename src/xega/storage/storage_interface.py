from abc import ABC, abstractmethod

from xega.common.configuration_types import (
    BenchmarkResult,
    ExpandedXegaBenchmarkConfig,
    GameMapResults,
)


# NB: this interface is for a single benchmark_id, so its not really appropriate for
# browsing multiple benchmark results. That might need to be reconsidered depending on
# how we want to use the storage system.
class Storage(ABC):
    def __init__(self, benchmark_id: str):
        self.benchmark_id = benchmark_id

    @abstractmethod
    async def get_config(self) -> ExpandedXegaBenchmarkConfig | None:
        pass

    @abstractmethod
    async def store_config(self, config: ExpandedXegaBenchmarkConfig):
        pass

    @abstractmethod
    async def get_game_map_results(
        self, game_name: str, map_seed: str, player_id: str
    ) -> GameMapResults | None:
        pass

    @abstractmethod
    async def store_game_map_results(self, results: GameMapResults):
        pass

    @abstractmethod
    async def get_benchmark_results(self) -> BenchmarkResult | None:
        pass
