import argparse
import json
import os
import re
from copy import deepcopy
from typing import cast

from xent.common.configuration_types import BenchmarkResult


def derive_output_path(input_path: str, game_name: str) -> str:
    base, ext = os.path.splitext(input_path)
    if not ext:
        ext = ".json"
    sanitized_game = re.sub(r"[^A-Za-z0-9_-]+", "-", game_name).strip("-")
    if not sanitized_game:
        sanitized_game = "game"
    return f"{base}_without_{sanitized_game}{ext}"


def remove_game_from_benchmark(
    benchmark: BenchmarkResult, game_name: str
) -> BenchmarkResult:
    if "expanded_config" not in benchmark or "results" not in benchmark:
        raise ValueError("Input does not look like a BenchmarkResult payload")

    updated_benchmark = deepcopy(benchmark)
    expanded_config = updated_benchmark["expanded_config"]

    games = expanded_config.get("games", [])
    maps_ = expanded_config.get("maps", [])
    results = updated_benchmark.get("results", [])

    filtered_games = [game for game in games if game.get("name") != game_name]
    filtered_maps = [game_map for game_map in maps_ if game_map.get("name") != game_name]
    filtered_results = [
        result for result in results if result.get("game_map", {}).get("name") != game_name
    ]

    if (
        len(filtered_games) == len(games)
        and len(filtered_maps) == len(maps_)
        and len(filtered_results) == len(results)
    ):
        raise ValueError(f"Game '{game_name}' was not found in the benchmark data")

    expanded_config["games"] = filtered_games
    expanded_config["maps"] = filtered_maps
    updated_benchmark["results"] = filtered_results

    return cast(BenchmarkResult, updated_benchmark)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Remove a game from a BenchmarkResult JSON payload, updating the expanded "
            "configuration and results."
        )
    )
    parser.add_argument("json_path", help="Path to the BenchmarkResult JSON file")
    parser.add_argument("game_name", help="Name of the game to remove")
    parser.add_argument(
        "--output",
        help="Optional output path for the updated benchmark JSON file",
    )

    args = parser.parse_args()

    input_path = args.json_path
    game_name = args.game_name
    output_path = args.output or derive_output_path(input_path, game_name)

    try:
        with open(input_path, "r", encoding="utf-8") as infile:
            benchmark_data = cast(BenchmarkResult, json.load(infile))

        updated_benchmark = remove_game_from_benchmark(benchmark_data, game_name)

        with open(output_path, "w", encoding="utf-8") as outfile:
            json.dump(updated_benchmark, outfile, indent=2)
            outfile.write("\n")

        print(f"Wrote updated benchmark without '{game_name}' to {output_path}")

    except FileNotFoundError as exc:
        raise SystemExit(f"Error: '{input_path}' not found") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: could not decode JSON from '{input_path}'") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
