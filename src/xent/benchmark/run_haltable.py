import logging
from typing import Any

from xent.common.configuration_types import ExecutableGameMap
from xent.runtime.execution import Results, State, run_haltable_game
from xent.runtime.judge import Judge
from xent.runtime.players.players import make_npcs, make_player
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_globals, build_locals


async def start_haltable_game(
    executable_game_map: ExecutableGameMap,
    judge: Judge | None,
) -> Results | State:
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
    lines = [line.strip() for line in game_code.split("\n")]

    logging.info(f"Running game: {game_str}")
    game_results = await run_haltable_game(
        lines, 0, xrt, executable_game_map["metadata"]["num_rounds_per_game"], 0, []
    )
    if game_results["kind"] == "results":
        logging.info("Haltable game completed")
        return game_results
    else:
        serialized_game_state = {
            "game_state": game_results["state"],
            "judge": judge.serialize(),
        }
        return {"kind": "state", "state": serialized_game_state}


# Bug: this currently duplicates the elicit request event. I could just cut it from
# this history, but that seems a bit severe to me. I'll leave the bug in for now and
# address if its needed.
async def resume_haltable_game(
    state: dict[str, Any], judge: Judge | None = None
) -> Results | State:
    if judge is None:
        judge = Judge.deserialize(state["judge"])
    globals = build_globals(judge)
    xrt = XentRuntime.deserialize(state["game_state"]["runtime"], globals)
    lines: list[str] = state["game_state"]["lines"]
    line_index: int = state["game_state"]["line_index"]
    rounds_played = state["game_state"]["rounds_played"]
    round_results = state["game_state"]["round_results"]
    num_rounds = state["game_state"]["num_rounds"]

    logging.info("Resuming game")
    game_results = await run_haltable_game(
        lines, line_index, xrt, num_rounds, rounds_played, round_results
    )
    if game_results["kind"] == "results":
        logging.info("Haltable game completed")
        return game_results
    else:
        serialized_game_state = {
            "game_state": game_results["state"],
            "judge": judge.serialize(),
        }
        return {"kind": "state", "state": serialized_game_state}
