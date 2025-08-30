import json
import logging
import os

from xega.common.configuration_types import (
    BenchmarkResult,
    ExpandedXegaBenchmarkConfig,
    GameMapResults,
)
from xega.common.util import dumps, generate_executable_game_maps
from xega.storage.storage_interface import Storage


# TODO needs exception handling
class DirectoryStorage(Storage):
    def __init__(self, storage_dir: str, benchmark_id: str):
        super().__init__(benchmark_id)
        self.storage_dir = storage_dir
        self.results_dir = os.path.join(self.storage_dir, self.benchmark_id)

    async def initialize(self):
        os.makedirs(self.results_dir, exist_ok=True)

    async def clear(self):
        logging.info(f"Cleaning results directory: {self.results_dir}")
        for root, dirs, files in os.walk(self.results_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    async def get_config(self) -> ExpandedXegaBenchmarkConfig | None:
        config_path = os.path.join(self.results_dir, "benchmark_config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                return config
        return None

    async def store_config(self, config: ExpandedXegaBenchmarkConfig):
        with open(os.path.join(self.results_dir, "benchmark_config.json"), "w") as f:
            f.write(dumps(config, indent=4))

    async def get_game_map_results(
        self, game_name: str, map_seed: str, player_id: str
    ) -> GameMapResults | None:
        results_path = os.path.join(
            self.results_dir,
            self._game_results_json_filename(game_name, map_seed, player_id),
        )
        if os.path.exists(results_path):
            with open(results_path) as f:
                game_results = json.load(f)
                return game_results
        return None

    async def store_game_map_results(self, results: GameMapResults):
        player_id = results["player"]["id"]
        game_name = results["game_map"]["name"]
        map_seed = results["game_map"]["map_seed"]
        with open(
            os.path.join(
                self.results_dir,
                self._game_results_json_filename(game_name, map_seed, player_id),
            ),
            "w",
        ) as f:
            f.write(dumps(results, indent=4))

    async def get_benchmark_results(self) -> BenchmarkResult | None:
        config = await self.get_config()
        if config is None:
            logging.info(f"No config found for benchmark {self.benchmark_id}")
            return None

        results: list[GameMapResults] = []
        game_maps = generate_executable_game_maps(config)
        for game_map in game_maps:
            game_map_results = await self.get_game_map_results(
                game_map["game_map"]["name"],
                game_map["game_map"]["map_seed"],
                game_map["player"]["id"],
            )
            if game_map_results is not None:
                results.append(game_map_results)

        return {"expanded_config": config, "results": results}

    def _game_results_json_filename(
        self, game_name: str, map_seed: str, player_id: str
    ) -> str:
        return f"game_{game_name}_{map_seed}_{player_id}.json"
