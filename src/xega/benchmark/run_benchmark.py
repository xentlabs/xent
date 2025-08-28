import asyncio
import json
import logging
import os

from xega.common.configuration_types import (
    BenchmarkResult,
    ExecutableGameMap,
    ExpandedXegaBenchmarkConfig,
    GameMapResults,
    PlayerName,
    TokenUsage,
    XegaBenchmarkResult,
    XegaGameConfig,
    XegaGameIterationResult,
    XegaGameResult,
)
from xega.common.util import dumps
from xega.common.version import get_xega_version, validate_version
from xega.runtime.base_player import XGP
from xega.runtime.execution import play_game
from xega.runtime.judge import Judge
from xega.runtime.players import make_player
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals


async def run_game(
    game_config: XegaGameConfig, judge: Judge | None, raise_on_error: bool = False
) -> XegaGameResult | None:
    game_name = game_config["game"]["name"]
    game_code = game_config["game"]["code"]
    player_configs = game_config["players"]
    if judge is None:
        judge = Judge(game_config["judge_model"])
        judge.set_seed(game_config["seed"], "")
    players: list[XGP] = []
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
            num_rounds=game_config["num_rounds_per_game"],
        )
        logging.info(f"Game {game_name} completed successfully")

        scores = extract_scores(game_results)
        token_usage = extract_token_usage(game_results)
        return XegaGameResult(
            game=game_config,
            game_results=game_results,
            scores=scores,
            token_usage=token_usage,
        )
    except Exception as e:
        logging.exception(
            f"Game {game_name} execution failed with exception: {e}", exc_info=True
        )
        if raise_on_error:
            raise e
        return None


def extract_token_usage(
    game_results: list[XegaGameIterationResult],
) -> dict[PlayerName, TokenUsage]:
    total_token_usage: dict[PlayerName, TokenUsage] = {}
    for game_result in game_results:
        token = game_result["token_usage"]
        for player, token_usage in token.items():
            if player not in total_token_usage:
                total_token_usage[player] = token_usage
            else:
                total_token_usage[player]["input_tokens"] += token_usage["input_tokens"]
                total_token_usage[player]["output_tokens"] += token_usage[
                    "output_tokens"
                ]
    return total_token_usage


def extract_scores(
    game_results: list[XegaGameIterationResult],
) -> dict[PlayerName, float]:
    max_scores: dict[PlayerName, float] = {}
    for game_result in game_results:
        score = game_result["scores"]
        for player, player_score in score.items():
            if player not in max_scores:
                max_scores[player] = player_score
            else:
                if player_score > max_scores[player]:
                    max_scores[player] = player_score

    return max_scores


# TODO: use storage system
def write_benchmark_results(
    benchmark_result: BenchmarkResult, results_dir: str
) -> None:
    if results_dir:
        benchmark_id = benchmark_result["expanded_config"]["metadata"]["benchmark_id"]
        os.makedirs(results_dir, exist_ok=True)
        with open(
            os.path.join(results_dir, f"benchmark_{benchmark_id}.json"),
            "w",
        ) as f:
            f.write(dumps(benchmark_result, indent=4))


# TODO this should call out to the storage interface instead of directly to fs
def get_existing_game_results(
    results_dir: str, executable_game_map: ExecutableGameMap
) -> XegaGameResult | None:
    results_path = os.path.join(
        results_dir, game_results_json_filename(executable_game_map)
    )
    if os.path.exists(results_path):
        with open(results_path) as f:
            game_results = json.load(f)
            return game_results
    return None


def write_game_results(game_results: GameMapResults, results_dir: str):
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
        with open(
            os.path.join(results_dir, game_results_json_filename(game_results)),
            "w",
        ) as f:
            f.write(dumps(game_results, indent=4))


def game_results_json_filename(
    executable_game_map: ExecutableGameMap | GameMapResults,
) -> str:
    game_name = executable_game_map["game_map"]["name"]
    map_seed = executable_game_map["game_map"]["map_seed"]
    player_id = executable_game_map["player"]["id"]
    return f"game_{game_name}_{map_seed}_{player_id}.json"


def print_game_history(game_results: GameMapResults) -> None:
    game_name = game_results["game_map"]["name"]
    map_seed = game_results["game_map"]["map_seed"]
    player_id = game_results["player"]["id"]
    logging.info(f"History for game {game_name} ({map_seed}) for player {player_id}:")
    for game_result in game_results["round_results"]:
        for line in game_result["history"]:
            logging.info(line)
        logging.info(f"Score: {game_result['score']}")


def check_version(config: ExpandedXegaBenchmarkConfig):
    config_version = config["metadata"]["xega_version"]
    current_version = get_xega_version()
    is_valid, message = validate_version(config_version, current_version)
    if not is_valid:
        logging.warning(f"Version validation in run_benchmark: {message}")
    else:
        logging.debug(f"Version validation in run_benchmark: {message}")


async def run_benchmark(
    config: ExpandedXegaBenchmarkConfig,
    results_dir: str,
    max_concurrent_games: int,
) -> XegaBenchmarkResult:
    # TODO this should be calling the storage system
    with open(os.path.join(results_dir, "benchmark_config.json"), "w") as f:
        f.write(dumps(config, indent=4))

    check_version(config)

    work_units = generate_executable_game_maps(config)

    benchmark_result = BenchmarkResult(
        expanded_config=config, results=[], finished=False
    )

    benchmark_id = config["metadata"]["benchmark_id"]
    logging.info(f"Starting benchmark with Benchmark ID: {benchmark_id}.")

    semaphore = asyncio.Semaphore(max_concurrent_games)

    # TODO: instead of returning results, this should just store them in the storage and exit (None return)
    async def run_game_or_get_results(
        executable_game_map: ExecutableGameMap, judge: Judge
    ) -> GameMapResults | None:
        game_name = executable_game_map["game_map"]["name"]
        map_seed = executable_game_map["game_map"]["map_seed"]
        player_id = executable_game_map["player"]["id"]
        game_str = f"{game_name} ({map_seed}) with player {player_id}"

        async with semaphore:
            existing = get_existing_game_results(results_dir, executable_game_map)
            if existing:
                print(
                    f"Found existing results for game {game_str}, skipping execution."
                )
                return existing

            try:
                print(f"Executing game {game_str}")
                result = await run_game(executable_game_map, judge)
                if result:
                    print(f"Game {game_str} completed successfully")
                    # TODO updateme
                    write_game_results(result, results_dir)
                    print_game_history(result)
                else:
                    print(f"{game_str} failed to execute")
                return result
            except Exception as e:
                logging.exception(
                    f"Error running game {game_str}: {e}",
                    exc_info=True,
                )
                return None

    judge = Judge(config["metadata"]["judge_model"])
    tasks = [
        run_game_or_get_results(executable_game_map, judge)
        for executable_game_map in work_units
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    print(f"Benchmark {benchmark_id} completed")

    for result in results:
        if isinstance(result, BaseException):
            logging.error(f"Game failed with error: {result}")
        elif result:
            benchmark_result["results"].append(result)

    write_benchmark_results(benchmark_result, results_dir)
    logging.info(f"Benchmark ({benchmark_id}) completed")
    print(f"Benchmark ({benchmark_id}) completed")
    return benchmark_result


def generate_executable_game_maps(
    config: ExpandedXegaBenchmarkConfig,
) -> list[ExecutableGameMap]:
    game_maps: list[ExecutableGameMap] = []
    for map in config["maps"]:
        for player in config["players"]:
            game_maps.append(
                ExecutableGameMap(
                    game_map=map, metadata=config["metadata"], player=player
                )
            )
    return game_maps
