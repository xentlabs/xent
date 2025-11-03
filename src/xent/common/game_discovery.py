import importlib.resources as resources
from collections.abc import Iterable
from pathlib import Path

from xent.common.configuration_types import GameConfig
from xent.presentation.executor import get_default_presentation


def load_game_from_file(game_file_path: Path) -> GameConfig:
    """Load a single game from a .xent file, pairing with optional presentation.

    Looks for a sibling file named "<stem>_presentation.py". If not found, uses
    the default presentation implementation.
    """
    if not game_file_path.is_file():
        raise ValueError(f"Not a file: {game_file_path}")
    if game_file_path.suffix != ".xent":
        raise ValueError(f"Not a .xent file: {game_file_path}")

    game_name = game_file_path.stem
    game_code = game_file_path.read_text()

    presentation_function = get_default_presentation()
    presentation_path = game_file_path.with_name(f"{game_name}_presentation.py")
    if presentation_path.exists() and presentation_path.is_file():
        presentation_function = presentation_path.read_text()

    return GameConfig(
        name=game_name, code=game_code, presentation_function=presentation_function
    )


def discover_games_in_paths(paths: Iterable[Path]) -> list[GameConfig]:
    """Discover games from a mix of directories and explicit files.

    - Directories: include all immediate children matching *.xent (non-recursive)
    - Files: must be a .xent file
    - Deduplicates by resolved absolute path
    - Returns games sorted alphabetically by name (case-insensitive)
    """
    all_game_paths: set[Path] = set()
    for p in paths:
        if p.is_dir():
            all_game_paths.update(p.glob("*.xent"))
        elif p.is_file():
            if p.suffix != ".xent":
                raise ValueError(f"Not a .xent file: {p}")
            all_game_paths.add(p)
        else:
            raise ValueError(f"Path does not exist: {p}")

    # Deduplicate by resolved absolute path
    all_game_paths = {p.resolve() for p in all_game_paths}

    games = [load_game_from_file(p) for p in all_game_paths]

    # Sort alphabetically by name (case-insensitive)
    games.sort(key=lambda g: g["name"].lower())
    return games


def discover_games_in_dir(directory: Path) -> list[GameConfig]:
    """Convenience wrapper to discover games in a single directory."""
    if not directory.exists() or not directory.is_dir():
        return []
    return discover_games_in_paths([directory])


def discover_packaged_games() -> list[GameConfig]:
    """Discover packaged games bundled under xent.games.

    Enumerates *.xent files in the xent.games package and loads their code and
    optional companion "<name>_presentation.py" files. Returns games sorted by
    name (case-insensitive).
    """
    games: list[GameConfig] = []
    try:
        pkg = resources.files("xent.games")
    except Exception:
        return []

    try:
        xent_files = [p for p in pkg.iterdir() if p.name.endswith(".xent")]
    except Exception:
        return []

    for xf in xent_files:
        name = xf.name[:-5]  # strip .xent
        try:
            code = xf.read_text()
        except Exception:
            continue
        pres_code = get_default_presentation()
        pres_path = pkg.joinpath(f"{name}_presentation.py")
        try:
            if pres_path.is_file():
                pres_code = pres_path.read_text()
        except Exception:
            # keep default if read fails
            pass
        games.append(GameConfig(name=name, code=code, presentation_function=pres_code))

    games.sort(key=lambda g: g["name"].lower())
    return games
