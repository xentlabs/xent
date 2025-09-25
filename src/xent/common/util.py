import json
import logging
import os
import subprocess

from xent.common.configuration_types import (
    ExecutableGameMap,
    ExpandedXentBenchmarkConfig,
)
from xent.common.token_xent_list import TokenXentList, ValidatedBool
from xent.common.x_list import XList
from xent.common.x_string import XString


class XEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, XString):
            return str(o)
        elif isinstance(o, XList):
            return list(o.items)
        elif isinstance(o, tuple):
            return {"__tuple__": True, "items": list(o)}
        elif isinstance(o, TokenXentList):
            return {"__TokenXentList__": True, "pairs": o.pairs, "scale": o.scale}
        elif isinstance(o, ValidatedBool):
            return bool(o)
        return super().default(o)


# No need to load XString from JSON
def x_decoder(dct):
    if "__tuple__" in dct:
        return tuple(dct["items"])
    elif "__TokenXentList__" in dct:
        return TokenXentList(dct["pairs"], dct["scale"])
    return dct


def dumps(obj, **kwargs):
    return json.dumps(obj, cls=XEncoder, **kwargs)


def loads(s, **kwargs):
    return json.loads(s, object_hook=x_decoder, **kwargs)


# Used to place git commit hash and diff in logs, which is useful for ensuring reproducibility of benchmark results
def log_git_snapshot(repo_path="."):
    if not os.path.isdir(repo_path):
        logging.warning(f"Git snapshot failed: Directory not found at '{repo_path}'")
        return

    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            stderr=subprocess.PIPE,
            text=True,
        ).strip()
        logging.info(f"Git Commit: {commit_hash}")

        git_diff = subprocess.check_output(
            ["git", "diff", "HEAD"], cwd=repo_path, stderr=subprocess.PIPE, text=True
        ).strip()

        if git_diff:
            logging.info(
                "Git Diff (staged/unstaged changes against HEAD):\n%s", git_diff
            )
        else:
            logging.info("Git Diff: No local changes detected against HEAD.")

        untracked_files = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_path,
            stderr=subprocess.PIPE,
            text=True,
        ).strip()

        if untracked_files:
            logging.info("Untracked files:\n%s", untracked_files)

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.warning(
            "Could not retrieve Git snapshot. This might be because 'git' is not installed, "
            f"the path '{repo_path}' is not a Git repository, or it has no commits. Error: {e}"
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred while logging git snapshot: {e}")


def generate_executable_game_maps(
    config: ExpandedXentBenchmarkConfig,
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
