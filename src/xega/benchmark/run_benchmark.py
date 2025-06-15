import json
import logging
import os
import random
from typing import Dict, List

from xega.common.util import dumps
from xega.common.xega_types import (
    GameConfig,
    PlayerConfig,
    PlayerName,
    XegaBenchmarkConfig,
    XegaBenchmarkResult,
    XegaGameConfig,
    XegaGameIterationResult,
    XegaGameResult,
)
from xega.runtime.base_player import XGP
from xega.runtime.execution import play_game
from xega.runtime.judge import Judge
from xega.runtime.players import make_player
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals


def full_seed(game_config: XegaGameConfig) -> str:
    return f"{game_config["seed"]}_{game_config["map_seed"]}"


async def run_game(game_config: XegaGameConfig) -> XegaGameResult | None:
    random.seed(full_seed(game_config))
    game_name = game_config["game"]["name"]
    game_code = game_config["game"]["code"]
    player_configs = game_config["players"]
    model_utils = Judge(game_config["judge_model"])
    players: List[XGP] = []
    for player_config in player_configs:
        players.append(make_player(player_config["name"], game_config))

    locals = build_locals(players, game_config)
    globals = build_globals(model_utils, full_seed(game_config))

    xrt = XegaRuntime(players, locals, globals)

    logging.info(
        f"Running game: {game_name} for players: {[p['id'] for p in player_configs]}"
    )
    try:
        game_results = await play_game(
            game_code,
            xrt,
            auto_replay=game_config["auto_replay"],
            max_steps=game_config["max_steps"],
        )
        logging.info(f"Game {game_name} completed successfully")

        scores = extract_scores(game_results)
        return XegaGameResult(
            game=game_config,
            game_results=game_results,
            scores=scores,
        )
    except Exception as e:
        logging.exception(
            f"Game {game_name} execution failed with exception: {e}", exc_info=True
        )
        return None


def extract_scores(
    game_results: List[XegaGameIterationResult],
) -> Dict[PlayerName, float]:
    max_scores: Dict[PlayerName, float] = {}
    for game_result in game_results:
        score = game_result["scores"]
        for player, player_score in score.items():
            if player not in max_scores:
                max_scores[player] = player_score
            else:
                if player_score > max_scores[player]:
                    max_scores[player] = player_score

    return max_scores


def write_benchmark_results(
    benchmark_result: XegaBenchmarkResult, results_dir: str
) -> None:
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
        with open(
            os.path.join(
                results_dir,
                f"benchmark_{benchmark_result['config']['benchmark_id']}.json",
            ),
            "w",
        ) as f:
            f.write(dumps(benchmark_result, indent=4))


def get_existing_game_results(
    results_dir: str, game_config: XegaGameConfig
) -> XegaGameResult | None:
    results_path = os.path.join(results_dir, game_results_json_filename(game_config))
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            game_results = json.load(f)
            if (
                game_results["game"]["game"]["name"] == game_config["game"]["name"]
                and game_results["game"]["players"][0]["id"]
                == game_config["players"][0]["id"]
                and game_results["game"]["map_seed"] == game_config["map_seed"]
            ):
                return game_results


def write_game_results(game_results: XegaGameResult, results_dir: str):
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
        with open(
            os.path.join(results_dir, game_results_json_filename(game_results["game"])),
            "w",
        ) as f:
            f.write(dumps(game_results, indent=4))


def game_results_json_filename(game_config: XegaGameConfig) -> str:
    return f"game_{game_config["game"]["name"]}_{game_config["players"][0]["id"]}_{game_config["map_seed"]}.json"


def print_game_history(game_results: XegaGameResult) -> None:
    logging.info(f"History for game {game_results["game"]["game"]['name']}:")
    for game_result in game_results["game_results"]:
        for line in game_result["xrt_history"]:
            logging.info(line)
        logging.info(f"Scores: {game_result['scores']}")


def build_game_configs_from_benchmark_config(
    game: GameConfig, benchmark_config: XegaBenchmarkConfig, player: PlayerConfig
) -> List[XegaGameConfig]:
    game_configs: List[XegaGameConfig] = []
    for map_num in range(benchmark_config["num_maps_per_game"]):
        map_seed = f"{map_num}"
        logging.debug(f"Using map seed: {map_seed}")
        game_configs.append(
            XegaGameConfig(
                judge_model=benchmark_config["judge_model"],
                npc_players=benchmark_config["npc_players"],
                num_variables_per_register=benchmark_config[
                    "num_variables_per_register"
                ],
                max_steps=benchmark_config["max_steps"],
                auto_replay=benchmark_config["auto_replay"],
                seed=benchmark_config["seed"],
                game=game,
                players=[player],
                num_maps_per_game=benchmark_config["num_maps_per_game"],
                map_seed=map_seed,
            )
        )

    return game_configs


async def run_benchmark(
    benchmark_config: XegaBenchmarkConfig, results_dir: str
) -> XegaBenchmarkResult:
    with open(os.path.join(results_dir, "benchmark_config.json"), "w") as f:
        f.write(dumps(benchmark_config, indent=4))

    benchmark_result = XegaBenchmarkResult(config=benchmark_config, game_results=[])
    logging.info(
        f"Starting benchmark with Benchmark ID: {benchmark_result['config']['benchmark_id']}"
    )
    for game in benchmark_config["games"]:
        for player_set in benchmark_config["players"]:
            if len(player_set) != 1:
                raise Exception("Currently only single player benchmarks are supported")
            player = player_set[0]
            logging.info(f"Running game {game['name']} for player {player["id"]}")
            game_configs = build_game_configs_from_benchmark_config(
                game, benchmark_config, player
            )
            for game_config in game_configs:
                existing_game_results = get_existing_game_results(
                    results_dir, game_config
                )
                if existing_game_results:
                    logging.info(
                        f"Skipping game {game_config['game']['name']} for player {player['id']} since its already completed"
                    )
                    benchmark_result["game_results"].append(existing_game_results)
                    continue

                game_results = await run_game(game_config)
                if game_results:
                    write_game_results(game_results, results_dir)
                    benchmark_result["game_results"].append(game_results)
                    print_game_history(game_results)
                else:
                    logging.error(
                        f"Game {game_config['game']['name']} execution failed, no results returned"
                    )

    write_benchmark_results(benchmark_result, results_dir)

    logging.info(f"Benchmark ({benchmark_result['config']['benchmark_id']}) completed")
    return benchmark_result
