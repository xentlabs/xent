import os

import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer

from xent.common.configuration_types import ExecutableGameMap
from xent.common.version import get_xent_version
from xent.presentation.executor import get_default_turn_presentation
from xent.runtime.default_players import MockXGP
from xent.runtime.judge import Judge
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_globals, build_locals

FAKE_GAME_MAP: ExecutableGameMap = {
    "game_map": {
        "name": "Fake Game",
        "code": "fake_code",
        "map_seed": "test_seed_0",
        "presentation_function": get_default_turn_presentation(),
    },
    "metadata": {
        "benchmark_id": "",
        "xent_version": get_xent_version(),
        "num_rounds_per_game": 30,
        "judge_model": "gpt2",
        "seed": "test_seed",
        "store_full_player_interactions": False,
    },
    "player": {
        "name": "black",
        "id": "gpt-4o",
        "player_type": "default",
        "options": {"model": "gpt-4o", "provider": "openai"},
    },
}


def pytest_addoption(parser):
    """Add command line options for test configuration"""
    parser.addoption(
        "--skip-model-cache",
        action="store_true",
        default=False,
        help="Skip pre-caching of ML models before tests run",
    )


def pytest_configure(config):
    """Pre-cache models before tests run, then enable offline mode"""
    if config.getoption("--skip-model-cache"):
        print("⏭️  Skipping model pre-caching (--skip-model-cache enabled)")
        return

    # Models used in tests
    models_to_cache = ["gpt2", "Qwen/Qwen3-0.6B-Base"]

    print("🔄 Pre-caching models for tests...")
    cached_models = []

    for model_name in models_to_cache:
        try:
            print(f"   Caching {model_name}...")
            # Cache with network access, then verify local cache works
            AutoTokenizer.from_pretrained(model_name)
            AutoModelForCausalLM.from_pretrained(model_name)

            # Test that local-only loading works
            AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            AutoModelForCausalLM.from_pretrained(model_name, local_files_only=True)

            cached_models.append(model_name)
            print(f"   ✅ {model_name} cached and verified for local-only access")
        except Exception as e:
            print(f"   ❌ Failed to cache {model_name}: {e}")
            print("   ⚠️  Tests may make network requests for this model")

    # Enable offline mode if we successfully cached models
    if cached_models:
        # Set multiple environment variables for comprehensive offline mode
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        print(f"🔒 Enabled offline mode for tests ({len(cached_models)} models cached)")
    else:
        print("⚠️  No models were cached - tests will run with network access")


def pytest_unconfigure(config):
    """Clean up after tests"""
    env_vars_to_clean = [
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
    ]
    cleaned = []

    for var in env_vars_to_clean:
        if var in os.environ:
            del os.environ[var]
            cleaned.append(var)

    if cleaned:
        print(f"🔓 Disabled offline mode ({', '.join(cleaned)})")


@pytest.fixture
def xrt():
    """Create a test XentRuntime instance."""
    executable_game_map = FAKE_GAME_MAP.copy()
    player = MockXGP("black", "mock_black_id", {}, executable_game_map)
    locals = build_locals(player, executable_game_map)
    judge = Judge("gpt2")
    globals = build_globals(judge)
    return XentRuntime(player, locals, globals)
