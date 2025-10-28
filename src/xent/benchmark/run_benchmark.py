import asyncio
import logging

from xent.common.configuration_types import (
    BenchmarkResult,
    ExecutableGameMap,
    ExpandedXentBenchmarkConfig,
    GameMapResults,
    GameMapRoundResult,
)
from xent.common.errors import XentInternalError
from xent.common.util import generate_executable_game_maps
from xent.common.version import get_xent_version, validate_version
from xent.common.xent_event import TokenUsage
from xent.runtime.execution import play_game
from xent.runtime.judge import Judge
from xent.runtime.players.players import make_npcs, make_player
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_globals, build_locals
from xent.storage.storage_interface import BenchmarkStorage


async def run_game(
    executable_game_map: ExecutableGameMap,
    judge: Judge | None,
    raise_on_error: bool = False,
    always_return_results: bool = False,
) -> GameMapResults | None:
    game_name = executable_game_map["game_map"]["name"]
    map_seed = executable_game_map["game_map"]["map_seed"]
    player_id = executable_game_map["player"]["id"]
    game_code = executable_game_map["game_map"]["code"]
    game_str = f"{game_name} ({map_seed}) for player: {player_id}"

    if judge is None:
        judge = Judge(executable_game_map["metadata"]["judge_model"])
        judge.set_seed(executable_game_map["metadata"]["seed"], "")

    player = make_player(executable_game_map)
    npcs = make_npcs(executable_game_map)
    locals = build_locals(player, npcs, executable_game_map)
    globals = build_globals(judge)

    xrt = XentRuntime(
        player,
        npcs,
        locals,
        globals,
        store_full_interactions=executable_game_map["metadata"].get(
            "store_full_player_interactions", False
        ),
    )

    logging.info(f"Running game: {game_str}")
    try:
        game_results = await play_game(
            game_code,
            xrt,
            num_rounds=executable_game_map["metadata"]["num_rounds_per_game"],
            always_return_results=always_return_results,
        )
        logging.info(f"Game {game_str} completed successfully")

        score = extract_score(game_results)
        token_usage = extract_token_usage(game_results)
        return GameMapResults(
            game_map=executable_game_map["game_map"],
            metadata=executable_game_map["metadata"],
            player=executable_game_map["player"],
            score=score,
            token_usage=token_usage,
            round_results=game_results,
        )
    except Exception as e:
        logging.exception(
            f"Game {game_str} execution failed with exception: {e}", exc_info=True
        )
        if raise_on_error:
            raise e
        return None


def extract_token_usage(
    game_results: list[GameMapRoundResult],
) -> TokenUsage:
    total_token_usage: TokenUsage = {"input_tokens": 0, "output_tokens": 0}
    for game_result in game_results:
        token_usage = game_result["token_usage"]
        total_token_usage["input_tokens"] += token_usage["input_tokens"]
        total_token_usage["output_tokens"] += token_usage["output_tokens"]

    return total_token_usage


def extract_score(
    game_results: list[GameMapRoundResult],
) -> float:
    max_score = game_results[0]["score"]

    for game_result in game_results:
        if game_result["score"] > max_score:
            max_score = game_result["score"]

    return max_score


def print_game_history(game_results: GameMapResults) -> None:
    game_name = game_results["game_map"]["name"]
    map_seed = game_results["game_map"]["map_seed"]
    player_id = game_results["player"]["id"]
    logging.info(f"History for game {game_name} ({map_seed}) for player {player_id}:")
    for game_result in game_results["round_results"]:
        for line in game_result["history"]:
            logging.info(line)
        logging.info(f"Score: {game_result['score']}")


def check_version(config: ExpandedXentBenchmarkConfig):
    config_version = config["metadata"]["xent_version"]
    current_version = get_xent_version()
    is_valid, message = validate_version(config_version, current_version)
    if not is_valid:
        logging.warning(f"Version validation in run_benchmark: {message}")
    else:
        logging.debug(f"Version validation in run_benchmark: {message}")


async def run_benchmark(
    config: ExpandedXentBenchmarkConfig,
    storage: BenchmarkStorage,
    max_concurrent_games: int,
) -> BenchmarkResult:
    await storage.set_running_state(True)
    await storage.store_config(config)
    try:
        check_version(config)

        work_units = generate_executable_game_maps(config)

        benchmark_id = config["metadata"]["benchmark_id"]
        logging.info(f"Starting benchmark with Benchmark ID: {benchmark_id}.")

        semaphore = asyncio.Semaphore(max_concurrent_games)

        async def run_game_or_get_results(
            executable_game_map: ExecutableGameMap, judge: Judge
        ) -> GameMapResults | None:
            game_name = executable_game_map["game_map"]["name"]
            map_seed = executable_game_map["game_map"]["map_seed"]
            player_id = executable_game_map["player"]["id"]
            game_str = f"{game_name} ({map_seed}) with player {player_id}"

            async with semaphore:
                existing = await storage.get_game_map_results(
                    game_name, map_seed, player_id
                )
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
                        await storage.store_game_map_results(result)
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

        await asyncio.gather(*tasks, return_exceptions=True)

        print(f"Benchmark {benchmark_id} completed")
        benchmark_result = await storage.get_benchmark_results()
        if benchmark_result is None:
            logging.error(f"Could not find benchmark results for {benchmark_id}")
            raise XentInternalError("Could not find benchmark results after execution")

        logging.info(f"Benchmark ({benchmark_id}) completed")
        print(f"Benchmark ({benchmark_id}) completed")
        return benchmark_result
    finally:
        await storage.set_running_state(False)
