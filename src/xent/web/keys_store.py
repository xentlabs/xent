import contextlib
import json
import os
from collections.abc import Mapping
from pathlib import Path

from xent.common.paths import results_root

# Supported provider environment variables
SUPPORTED_KEYS: list[str] = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    # Not a key, but useful for Ollama connectivity
    "OLLAMA_HOST",
]


def _results_dir() -> Path:
    """Return the results directory used by the web server.

    Matches the global results root configured for the application and honors
    environment-based overrides.
    """
    return results_root()


def get_keystore_path() -> Path:
    return _results_dir() / ".api_keys.json"


def _ensure_results_dir() -> None:
    _results_dir().mkdir(parents=True, exist_ok=True)


def load_keystore() -> dict[str, str]:
    """Load the keystore from disk. Returns an empty dict if not present.

    Only returns keys in SUPPORTED_KEYS and with string values.
    """
    path = get_keystore_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            store: dict[str, str] = {}
            for k, v in data.items():
                if k in SUPPORTED_KEYS and isinstance(v, str) and v:
                    store[k] = v
            return store
    except Exception:
        # If the keystore is malformed or unreadable, treat as empty for safety
        return {}


def save_keystore(new_store: Mapping[str, str]) -> None:
    """Persist the keystore to disk with restrictive permissions."""
    _ensure_results_dir()
    path = get_keystore_path()
    # Filter to supported keys with non-empty strings
    filtered = {
        k: v
        for k, v in new_store.items()
        if k in SUPPORTED_KEYS and isinstance(v, str) and v
    }
    with open(path, "w") as f:
        json.dump(filtered, f, indent=2)

    with contextlib.suppress(Exception):
        # Best-effort restrict perms (POSIX)
        os.chmod(path, 0o600)


def update_keystore(partial: Mapping[str, str | None]) -> dict[str, str]:
    """Apply partial updates to the keystore. None or empty string removes a key."""
    current = load_keystore()
    for k, v in partial.items():
        if k not in SUPPORTED_KEYS:
            continue
        if v is None or (isinstance(v, str) and v.strip() == ""):
            if k in current:
                current.pop(k, None)
        else:
            current[k] = str(v)
    save_keystore(current)
    return current


def mask(value: str) -> str:
    """Return a masked representation of a secret value."""
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


def effective_keys(
    env: Mapping[str, str] | None = None, keystore: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Compute effective keys where environment takes precedence over keystore.

    Returns a mapping of key->value for those keys that are set by either source.
    """
    env = env or os.environ
    keystore = keystore or load_keystore()
    result: dict[str, str] = {}
    for k in SUPPORTED_KEYS:
        v = env.get(k) or keystore.get(k, "")
        if isinstance(v, str) and v:
            result[k] = v
    return result


def effective_summary(
    env: Mapping[str, str] | None = None, keystore: Mapping[str, str] | None = None
) -> list[dict[str, str | bool]]:
    """Summarize key presence and source without leaking values."""
    env = env or os.environ
    keystore = keystore or load_keystore()
    summary: list[dict[str, str | bool]] = []
    for k in SUPPORTED_KEYS:
        if env.get(k):
            summary.append(
                {
                    "name": k,
                    "set": True,
                    "source": "env",
                    "last4": (env.get(k) or "")[-4:],
                }
            )
        elif keystore.get(k):
            summary.append(
                {
                    "name": k,
                    "set": True,
                    "source": "keystore",
                    "last4": (keystore.get(k) or "")[-4:],
                }
            )
        else:
            summary.append({"name": k, "set": False, "source": "unset"})
    return summary


def apply_keystore_to_env(keystore: Mapping[str, str] | None = None) -> None:
    """Apply keystore values to environment without overriding existing env vars."""
    keystore = keystore or load_keystore()
    for k in SUPPORTED_KEYS:
        if os.environ.get(k):
            continue
        v = keystore.get(k)
        if isinstance(v, str) and v:
            os.environ[k] = v


def bootstrap_from_env_to_keystore_if_missing() -> None:
    """If keystore is absent, initialize it from current environment (if any keys found)."""
    path = get_keystore_path()
    if path.exists():
        return
    # Build from environment
    collected: dict[str, str] = {}
    for k in SUPPORTED_KEYS:
        v = os.environ.get(k)
        if isinstance(v, str) and v:
            collected[k] = v
    if collected:
        save_keystore(collected)


def required_env_for_providers(providers: set[str]) -> set[str]:
    """Map provider names to required environment variables.

    Ollama does not require a key (optionally uses OLLAMA_HOST), and HuggingFace
    models may not require a token for local usage; we do not enforce an HF token here.
    """
    mapping: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "grok": "GROK_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
    }
    required: set[str] = set()
    for p in providers:
        key = mapping.get(p)
        if key:
            required.add(key)
    return required
