import json
import logging
from pathlib import Path

from xent.common.configuration_types import (
    BenchmarkResult,
    ExpandedXentBenchmarkConfig,
    GameMapResults,
)
from xent.common.util import dumps, generate_executable_game_maps
from xent.storage.storage_interface import BenchmarkStorage, Storage


# TODO needs exception handling
class DirectoryBenchmarkStorage(BenchmarkStorage):
    def __init__(self, storage_dir: Path, benchmark_id: str):
        super().__init__(benchmark_id)
        self.storage_dir = storage_dir
        self.results_dir = self.storage_dir / self.benchmark_id

    async def initialize(self):
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def clear(self):
        logging.info(f"Cleaning results directory: {self.results_dir}")
        if self.results_dir.exists():
            for item in self.results_dir.rglob("*"):
                if item.is_file():
                    item.unlink()
            for item in sorted(self.results_dir.rglob("*"), reverse=True):
                if item.is_dir():
                    item.rmdir()

    async def get_config(self) -> ExpandedXentBenchmarkConfig | None:
        config_path = self.results_dir / "benchmark_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config
        return None

    async def store_config(self, config: ExpandedXentBenchmarkConfig):
        config_path = self.results_dir / "benchmark_config.json"
        with open(config_path, "w") as f:
            f.write(dumps(config, indent=4))

    async def get_game_map_results(
        self, game_name: str, map_seed: str, player_id: str
    ) -> GameMapResults | None:
        results_path = self.results_dir / self._game_results_json_filename(
            game_name, map_seed, player_id
        )
        if results_path.exists():
            with open(results_path) as f:
                game_results = json.load(f)
                return game_results
        return None

    async def store_game_map_results(self, results: GameMapResults):
        player_id = results["player"]["id"]
        game_name = results["game_map"]["name"]
        map_seed = results["game_map"]["map_seed"]
        results_path = self.results_dir / self._game_results_json_filename(
            game_name, map_seed, player_id
        )
        with open(results_path, "w") as f:
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

    async def get_running_state(self) -> bool:
        run_status_path = self.results_dir / "running_state.txt"
        if run_status_path.exists() and run_status_path.is_file():
            with open(run_status_path) as f:
                running_contents = f.read()
                return running_contents == "running"
        return False

    async def set_running_state(self, running: bool):
        run_status_path = self.results_dir / "running_state.txt"
        contents = "running" if running else "stopped"
        with open(run_status_path, "w") as f:
            f.write(contents)

    def _game_results_json_filename(
        self, game_name: str, map_seed: str, player_id: str
    ) -> Path:
        return Path(f"game_{game_name}_{map_seed}_{player_id}.json")


class DirectoryStorage(Storage):
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir

    async def list_configs(self) -> list[ExpandedXentBenchmarkConfig]:
        configs: list[ExpandedXentBenchmarkConfig] = []
        for item in self.storage_dir.iterdir():
            if item.is_dir():
                config_file = item / "benchmark_config.json"
                if config_file.exists() and config_file.is_file():
                    try:
                        with open(config_file) as f:
                            config_data = json.load(f)
                            configs.append(config_data)
                    except (OSError, json.JSONDecodeError) as e:
                        # Handle potential errors (malformed JSON, read errors)
                        print(f"Error reading {config_file}: {e}")
                        continue

        return configs

    async def add_config(self, config: ExpandedXentBenchmarkConfig):
        benchmark_storage = DirectoryBenchmarkStorage(
            self.storage_dir, config["metadata"]["benchmark_id"]
        )
        await benchmark_storage.initialize()
        await benchmark_storage.store_config(config)

    async def list_result_ids(self) -> set[str]:
        configs = await self.list_configs()
        valid_result_ids: set[str] = set()
        for config in configs:
            benchmark_storage = DirectoryBenchmarkStorage(
                self.storage_dir, config["metadata"]["benchmark_id"]
            )
            await benchmark_storage.initialize()
            results = await benchmark_storage.get_benchmark_results()
            if results is not None and len(results["results"]) > 0:
                valid_result_ids.add(config["metadata"]["benchmark_id"])
        return valid_result_ids

    async def get_result(self, benchmark_id: str) -> BenchmarkResult | None:
        benchmark_storage = DirectoryBenchmarkStorage(self.storage_dir, benchmark_id)
        await benchmark_storage.initialize()
        return await benchmark_storage.get_benchmark_results()
