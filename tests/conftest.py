import pytest

from xega.common.configuration_types import ExecutableGameMap
from xega.common.version import get_xega_version
from xega.presentation.executor import get_default_presentation
from xega.runtime.default_players import MockXGP
from xega.runtime.judge import Judge
from xega.runtime.runtime import XegaRuntime
from xega.runtime.variables import build_globals, build_locals

FAKE_GAME_MAP: ExecutableGameMap = {
    "game_map": {
        "name": "Fake Game",
        "code": "fake_code",
        "map_seed": "test_seed_0",
        "presentation_function": get_default_presentation(),
    },
    "metadata": {
        "benchmark_id": "",
        "xega_version": get_xega_version(),
        "num_rounds_per_game": 30,
        "judge_model": "gpt2",
        "seed": "test_seed",
    },
    "player": {
        "name": "black",
        "id": "gpt-4o",
        "player_type": "default",
        "options": {"model": "gpt-4o", "provider": "openai"},
    },
}


@pytest.fixture
def xrt():
    """Create a test XegaRuntime instance."""
    executable_game_map = FAKE_GAME_MAP.copy()
    player = MockXGP("black", "mock_black_id", {}, executable_game_map)
    locals = build_locals(player, executable_game_map)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    return XegaRuntime(player, locals, globals)
