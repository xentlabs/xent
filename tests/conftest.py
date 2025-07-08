import pytest

from xega.common.xega_types import XegaGameConfig
from xega.runtime.default_players import MockXGP
from xega.runtime.judge import Judge
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals

FAKE_GAME_CONFIG: XegaGameConfig = {
    "game": {
        "name": "Fake Game",
        "code": "fake_code",
        "map_seed": "test_seed_0",
    },
    "auto_replay": True,
    "max_steps": 100,
    "players": [
        {
            "name": "black",
            "id": "gpt-4o",
            "player_type": "default",
            "options": {"model": "gpt-4o", "provider": "openai"},
        },
        {
            "name": "white",
            "id": "gpt-4o",
            "player_type": "default",
            "options": {"model": "gpt-4o", "provider": "openai"},
        },
    ],
    "num_variables_per_register": 4,
    "num_maps_per_game": 1,
    "judge_model": "gpt2",
    "npc_players": [],
    "seed": "test_seed",
    "map_seed": "test_seed_0",
}


@pytest.fixture
def xrt():
    """Create a test XegaRuntime instance."""
    game_config = FAKE_GAME_CONFIG.copy()
    player = MockXGP("black", "mock_black_id", {}, game_config)
    locals = build_locals([player], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    return XegaRuntime([player], locals, globals)


@pytest.fixture
def xrt_multi_player():
    """Create a test XegaRuntime instance with multiple players."""
    game_config = FAKE_GAME_CONFIG.copy()
    alice = MockXGP("alice", "mock_alice_id", {}, game_config)
    bob = MockXGP("bob", "mock_bob_id", {}, game_config)
    locals = build_locals([alice, bob], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    return XegaRuntime([alice, bob], locals, globals)


@pytest.fixture
def xrt_zero_sum():
    """Create a test XegaRuntime instance with zero-sum players."""
    game_config = FAKE_GAME_CONFIG.copy()
    black = MockXGP("black", "mock_black_id", {}, game_config)
    white = MockXGP("white", "mock_white_id", {}, game_config)
    locals = build_locals([black, white], game_config)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    return XegaRuntime([black, white], locals, globals)
