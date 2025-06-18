import asyncio
import json
import logging
import os
from typing import Dict, List

from xega.common.util import dumps
from xega.common.xega_types import (
    ExpandedXegaBenchmarkConfig,
    PlayerName,
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


async def run_game(game_config: XegaGameConfig) -> XegaGameResult | None:
    game_name = game_config["game"]["name"]
    game_code = game_config["game"]["code"]
    player_configs = game_config["players"]
    judge = Judge(game_config["judge_model"])
    judge.set_seed(game_config["seed"], game_config["map_seed"])
    players: List[XGP] = []
    for player_config in player_configs:
        players.append(make_player(player_config["name"], game_config))

    locals = build_locals(players, game_config)
    globals = build_globals(judge)

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


async def run_benchmark(
    benchmark_config: ExpandedXegaBenchmarkConfig,
    results_dir: str,
    max_concurrent_games: int,
) -> XegaBenchmarkResult:
    with open(os.path.join(results_dir, "benchmark_config.json"), "w") as f:
        f.write(dumps(benchmark_config, indent=4))

    benchmark_result = XegaBenchmarkResult(config=benchmark_config, game_results=[])
    logging.info(
        f"Starting benchmark with Benchmark ID: {benchmark_result['config']['benchmark_id']}"
    )

    semaphore = asyncio.Semaphore(max_concurrent_games)

    async def run_game_with_retry(game_config):
        async with semaphore:
            existing = get_existing_game_results(results_dir, game_config)
            if existing:
                return existing

            result = await run_game(game_config)
            if result:
                write_game_results(result, results_dir)
                print_game_history(result)
            return result

    tasks = [
        run_game_with_retry(game_config) for game_config in benchmark_config["games"]
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, handling any exceptions
    for result in results:
        if isinstance(result, BaseException):
            logging.error(f"Game failed with error: {result}")
        elif result:
            benchmark_result["game_results"].append(result)

    write_benchmark_results(benchmark_result, results_dir)
    logging.info(f"Benchmark ({benchmark_result['config']['benchmark_id']}) completed")
    return benchmark_result
