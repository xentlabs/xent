import argparse
import json
from typing import cast

from xent.common.configuration_types import BenchmarkResult


def build_expected_pairs(benchmark: BenchmarkResult) -> dict[tuple[str, str, str], dict[str, str]]:
    expanded_config = benchmark["expanded_config"]
    players = expanded_config.get("players", [])
    maps = expanded_config.get("maps", [])

    expected: dict[tuple[str, str, str], dict[str, str]] = {}

    for game_map in maps:
        game_name = game_map.get("name")
        map_seed = game_map.get("map_seed")
        if game_name is None or map_seed is None:
            continue

        for player in players:
            player_id = player.get("id")
            if player_id is None:
                continue

            key = (cast(str, game_name), cast(str, map_seed), cast(str, player_id))
            expected[key] = {
                "game": cast(str, game_name),
                "map_seed": cast(str, map_seed),
                "player_id": cast(str, player_id),
                "player_name": str(player.get("name", "")),
            }

    return expected


def analyze_results(
    benchmark: BenchmarkResult,
) -> tuple[set[tuple[str, str, str]], list[dict[str, str | int]]]:
    results = benchmark.get("results", [])
    expanded_config = benchmark["expanded_config"]
    expected_rounds = expanded_config.get("metadata", {}).get("num_rounds_per_game")

    actual_pairs: set[tuple[str, str, str]] = set()
    incomplete_runs: list[dict[str, str | int]] = []

    for result in results:
        game_map = result.get("game_map", {})
        player = result.get("player", {})

        game_name = game_map.get("name")
        map_seed = game_map.get("map_seed")
        player_id = player.get("id")

        if game_name is None or map_seed is None or player_id is None:
            continue

        key = (cast(str, game_name), cast(str, map_seed), cast(str, player_id))
        actual_pairs.add(key)

        if isinstance(expected_rounds, int):
            round_results = result.get("round_results", [])
            actual_rounds = len(round_results)
            if actual_rounds != expected_rounds:
                incomplete_runs.append(
                    {
                        "game": cast(str, game_name),
                        "map_seed": cast(str, map_seed),
                        "player_id": cast(str, player_id),
                        "player_name": str(player.get("name", "")),
                        "expected_rounds": expected_rounds,
                        "actual_rounds": actual_rounds,
                    }
                )

    return actual_pairs, incomplete_runs


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a BenchmarkResult JSON file for missing game/map/player combinations "
            "and incomplete round data."
        )
    )
    parser.add_argument("json_path", help="Path to the BenchmarkResult JSON file")
    args = parser.parse_args()

    try:
        with open(args.json_path, "r", encoding="utf-8") as infile:
            benchmark_data = cast(BenchmarkResult, json.load(infile))
    except FileNotFoundError as exc:
        raise SystemExit(f"Error: '{args.json_path}' not found") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: could not decode JSON from '{args.json_path}'") from exc

    if "expanded_config" not in benchmark_data or "results" not in benchmark_data:
        raise SystemExit("Error: input does not appear to be a BenchmarkResult payload")

    expected_pairs = build_expected_pairs(benchmark_data)
    actual_pairs, incomplete_runs = analyze_results(benchmark_data)

    missing_pairs = sorted(set(expected_pairs) - actual_pairs)

    issues_found = False

    if missing_pairs:
        issues_found = True
        print("Missing results detected:")
        for game_name, map_seed, player_id in missing_pairs:
            metadata = expected_pairs[(game_name, map_seed, player_id)]
            player_name = metadata.get("player_name", "")
            extra = f" (player={player_name})" if player_name else ""
            print(
                f"  - game={metadata['game']} map_seed={metadata['map_seed']} "
                f"player_id={metadata['player_id']}{extra}"
            )

    if incomplete_runs:
        issues_found = True
        print("Incomplete results detected:")
        for entry in sorted(
            incomplete_runs,
            key=lambda item: (item["game"], item["map_seed"], item["player_id"]),
        ):
            player_name = entry.get("player_name", "") or ""
            extra = f" (player={player_name})" if player_name else ""
            print(
                f"  - game={entry['game']} map_seed={entry['map_seed']} "
                f"player_id={entry['player_id']}{extra}: "
                f"expected {entry['expected_rounds']} rounds, found {entry['actual_rounds']}"
            )

    if not issues_found:
        print("No missing or incomplete game/map/player results detected.")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
