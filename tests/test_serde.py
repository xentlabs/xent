import pytest

from xent.common.configuration_types import ExecutableGameMap
from xent.common.token_xent_list import TokenXentList
from xent.common.x_flag import XFlag
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    RevealEvent,
    RewardEvent,
    RoundFinishedEvent,
    RoundStartedEvent,
)
from xent.presentation.executor import get_default_presentation
from xent.runtime.players.default_players import MockXGP
from xent.runtime.runtime import XentRuntime


def make_executable_game_map() -> ExecutableGameMap:
    return {
        "game_map": {
            "name": "Serde Test Game",
            "code": 'elicit(s, 5)\nensure(s != "")',
            "map_seed": "serde_seed",
            "presentation_function": get_default_presentation(),
        },
        "metadata": {
            "benchmark_id": "bench",
            "xent_version": "0.0.0-test",
            "num_rounds_per_game": 1,
            "judge_model": "gpt2",
            "seed": "serde_seed",
            "store_full_player_interactions": True,
            "npcs": [],
        },
        "player": {
            "name": "black",
            "id": "mock_black_id",
            "player_type": "mock",
            "options": {},
        },
    }


@pytest.mark.asyncio
async def test_runtime_serialization_roundtrip():
    egm = make_executable_game_map()

    s = XString("hello", static=False, public=True, name="s")
    s.prefix = "pre: "
    lst = XList([XString("a"), XString("b")], static=False, public=True, name="l")
    player = MockXGP("black", "mock_black_id", {}, egm)
    npc = MockXGP("white", "mock_white_id", {}, egm)
    locals_dict = {"s": s, "l": lst, "black": player, "white": npc}
    xrt = XentRuntime(
        player, [npc], locals_dict, globals={}, store_full_interactions=True
    )
    xrt.beacons["flag_1"] = XFlag("flag_1", 1)
    xrt.replay_counters = {3: 1, 10: 2}
    xrt.score = 42.0
    xrt.add_token_usage({"input_tokens": 5, "output_tokens": 7})

    started: RoundStartedEvent = {
        "type": "round_started",
        "round_index": 0,
        "line": "elicit(s, 5)",
        "line_num": 1,
        "player": "black",
    }

    req: ElicitRequestEvent = {
        "type": "elicit_request",
        "line": "elicit(s, 5)",
        "line_num": 1,
        "player": "black",
        "var_name": "s",
        "max_len": 5,
        "registers": {"s": s, "l": lst},
    }

    resp: ElicitResponseEvent = {
        "type": "elicit_response",
        "line": "elicit(s, 5)",
        "line_num": 1,
        "player": "black",
        "response": "foo",
        "token_usage": {"input_tokens": 1, "output_tokens": 2},
        "prompts": [
            {"role": "user", "content": "prompt"},
            {"role": "system", "content": "inst"},
        ],
        "full_response": [
            {"role": "assistant", "content": "<move>foo</move>"},
        ],
    }

    rev: RevealEvent = {
        "type": "reveal",
        "line": "reveal(s, l)",
        "line_num": 2,
        "player": "black",
        "values": {"s": s, "l": lst},
    }

    rew: RewardEvent = {
        "type": "reward",
        "line": "reward(black, xent(s))",
        "line_num": 3,
        "player": "black",
        "value": TokenXentList([("", 1.0), ("foo", 2.0)]),
    }

    fail: FailedEnsureEvent = {
        "type": "failed_ensure",
        "line": 'ensure(s != "")',
        "line_num": 4,
        "player": "black",
        "ensure_results": [False, True],
        "beacon": "flag_1",
    }

    finished: RoundFinishedEvent = {
        "type": "round_finished",
        "round_index": 0,
        "line": 'ensure(s != "")',
        "line_num": 4,
        "player": "black",
    }

    for ev in [started, req, resp, rev, rew, fail, finished]:
        await xrt.send_event(player, ev)

    payload = xrt.serialize()

    assert set(payload.keys()) >= {
        "player",
        "npcs",
        "locals",
        "beacons",
        "score",
        "token_usage",
        "history",
        "replay_counters",
        "store_full_interactions",
    }

    xrt2 = XentRuntime.deserialize(payload, globals={})

    assert xrt2.score == 42.0
    assert xrt2.token_usage == {"input_tokens": 5, "output_tokens": 7}

    s2 = xrt2.local_vars["s"]
    assert isinstance(s2, XString)
    assert s2.primary_string == "hello"
    assert s2.prefix == "pre: "

    l2 = xrt2.local_vars["l"]
    assert isinstance(l2, XList)
    assert [str(it) for it in l2.items] == ["a", "b"]

    assert "flag_1" in xrt2.beacons
    assert isinstance(xrt2.beacons["flag_1"], XFlag)
    assert xrt2.beacons["flag_1"].line_num == 1
    assert xrt2.replay_counters == {3: 1, 10: 2}

    assert len(xrt2.history) == 7

    req2 = xrt2.history[1]
    assert req2["type"] == "elicit_request"
    assert isinstance(req2["registers"]["s"], XString)
    assert isinstance(req2["registers"]["l"], XList)

    resp2 = xrt2.history[2]
    assert resp2["type"] == "elicit_response"
    assert resp2["token_usage"] == {"input_tokens": 1, "output_tokens": 2}
    assert isinstance(resp2.get("prompts"), list)
    assert isinstance(resp2.get("full_response"), list)

    rev2 = xrt2.history[3]
    assert rev2["type"] == "reveal"
    assert isinstance(rev2["values"]["s"], XString)
    assert isinstance(rev2["values"]["l"], XList)

    rew2 = xrt2.history[4]
    assert rew2["type"] == "reward"
    assert isinstance(rew2["value"], TokenXentList)
