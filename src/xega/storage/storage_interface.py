from abc import ABC, abstractmethod

from xega.common.configuration_types import (
    BenchmarkResult,
    ExecutableGameMap,
    ExpandedXegaBenchmarkConfig,
    GameMapResults,
)


class Storage(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    async def list_configs(self) -> list[ExpandedXegaBenchmarkConfig]:
        pass

    @abstractmethod
    async def add_config(self, config: ExpandedXegaBenchmarkConfig):
        pass

    @abstractmethod
    async def list_result_ids(self) -> set[str]:
        pass

    @abstractmethod
    async def get_result(self, benchmark_id: str) -> BenchmarkResult | None:
        pass


class BenchmarkStorage(ABC):
    def __init__(self, benchmark_id: str):
        self.benchmark_id = benchmark_id

    @abstractmethod
    async def initialize(self):
        pass

    @abstractmethod
    async def clear(self):
        pass

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

    @abstractmethod
    async def get_running_state(self) -> bool:
        pass

    @abstractmethod
    async def set_running_state(self, running: bool):
        pass


class GameStorage(ABC):
    @abstractmethod
    async def initialize(self):
        pass

    # This always returns with empty player array
    @abstractmethod
    async def get_game_map(self, game_name: str) -> ExecutableGameMap:
        pass

    # NB: this will store with an empty player list. Throws if game is already stored
    @abstractmethod
    async def insert_game_map_config(self, game: ExecutableGameMap):
        pass

    # All objects have empty player list
    @abstractmethod
    async def list_game_map_configs(self) -> list[ExecutableGameMap]:
        pass

    # Effectively an upsert. Updates if the game map + player already exist
    @abstractmethod
    async def set_game_map_results(
        self, results: GameMapResults
    ) -> list[GameMapResults]:
        pass

    @abstractmethod
    async def get_game_map_results(self, game_name: str) -> list[GameMapResults]:
        pass
