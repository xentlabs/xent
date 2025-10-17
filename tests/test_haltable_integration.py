import pytest

from xent.benchmark.run_haltable import resume_haltable_game, start_haltable_game
from xent.common.configuration_types import ExecutableGameMap
from xent.presentation.executor import get_default_presentation


def _make_halting_egm() -> ExecutableGameMap:
    code = (
        'assign(s1="At the book club, I ran into this girl, Neila, who claims to only read books backwards: starting from the bottom-right corner of the last page and reading all the words in reverse order until the beginning, finishing with the title. Doesn\'t it spoil the fun of the story? Apparently not, she told me. The suspense is just distributed somewhat differently (some books\' beginnings are apparently all too predictable), and some books get better or worse if you read them in one direction or another. She started reading backwards at age seven. Her name was sort of a predisposition.", s2="Hello, it is today a lovely day to use my skills in differential geometry and in the calculus of variation to estimate how much grass I will be able to eat. I aim to produce a lot of milk and to write a lot of theorems for my children, because that\'s what the beauty of life is about, dear physicists and cheese-makers. Have a great day!")\n'
        "reveal(s1, s2)\n"
        "elicit(x, 20)\n"
        "reward(xent(x | s1))\n"
        "reward(-xent(s2 | (s1+x)))"
    )

    return {
        "game_map": {
            "name": "test_single_halting",
            "code": code,
            "map_seed": "halt_seed",
            "presentation_function": get_default_presentation(),
        },
        "metadata": {
            "benchmark_id": "halt_bench",
            "xent_version": "0.0.0",
            "num_rounds_per_game": 1,
            "judge_model": "gpt2",
            "seed": "halt_seed",
            "store_full_player_interactions": False,
            "npcs": [],
        },
        "player": {
            "name": "black",
            "id": "halting_black",
            "player_type": "halting",
            "options": {},
        },
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_haltable_game_resume_flow():
    egm = _make_halting_egm()

    start_result = await start_haltable_game(egm, judge=None)

    assert start_result["kind"] == "state"
    state = start_result["state"]

    runtime_player = state["game_state"]["runtime"]["player"]
    assert runtime_player.get("player_type") == "halting"
    runtime_player["next_move"] = "<move>hello</move>"

    end_result = await resume_haltable_game(state)

    assert end_result["kind"] == "results"
    results = end_result["results"]
    assert isinstance(results, list)
    assert len(results) == 1

    history = results[0]["history"]
    types = [e["type"] for e in history]

    assert "elicit_request" in types
    assert "elicit_response" in types
    assert types[-1] == "round_finished"

    elicit_resp = next(e for e in history if e["type"] == "elicit_response")
    assert isinstance(elicit_resp.get("response"), str)
    assert len(elicit_resp["response"]) > 0
