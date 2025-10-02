import argparse
import json
from collections import defaultdict
from pathlib import Path

from xent.common.configuration_types import BenchmarkResult, GameMapResults

PlayerId = str
GameName = str
PlayerScores = dict[PlayerId, float]


def group_game_results_by_player_and_game(
    benchmark_result: BenchmarkResult,
) -> dict[str, dict[str, list[GameMapResults]]]:
    """
    Returns dict[player_id -> dict[game_name -> list[GameMapResults]]
    """
    games_by_player: dict[str, list[GameMapResults]] = defaultdict(list[GameMapResults])

    for game_result in benchmark_result["results"]:
        player_id = game_result["player"]["id"]
        games_by_player[player_id].append(game_result)

    result = {}
    for player_id, game_results in games_by_player.items():
        games_by_name: dict[str, list[GameMapResults]] = defaultdict(
            list[GameMapResults]
        )
        for game_result in game_results:
            game_name = game_result["game_map"]["name"]
            games_by_name[game_name].append(game_result)

        result[player_id] = games_by_name

    return result


def compute_game_map_max_scores(
    benchmark_result: BenchmarkResult,
) -> dict[GameName, dict[str, float]]:
    """Collect the maximum raw score observed per game/map combination."""
    game_map_max_scores: dict[GameName, dict[str, float]] = {}

    for game_result in benchmark_result["results"]:
        game_name = game_result["game_map"]["name"]
        map_seed = game_result["game_map"]["map_seed"]
        score = game_result["score"]

        game_maxes = game_map_max_scores.setdefault(game_name, {})
        current_max = game_maxes.get(map_seed)
        if current_max is None or score > current_max:
            game_maxes[map_seed] = score

    return game_map_max_scores


def get_player_id_score_sum(
    grouped_data: dict[str, dict[str, list[GameMapResults]]],
    game_map_max_scores: dict[GameName, dict[str, float]],
) -> PlayerScores:
    """
    Calculates the total score for each player across all their games.
    """
    player_id_score_sum: PlayerScores = {}

    for player_id, games in grouped_data.items():
        per_game_sums = []
        for game_name, game_results in games.items():
            normalized_sum = 0.0
            valid_map_count = 0

            for game_result in game_results:
                map_seed = game_result["game_map"]["map_seed"]
                max_score = game_map_max_scores.get(game_name, {}).get(map_seed)

                if max_score is None or abs(max_score) == 0:
                    continue

                normalized_score = game_result["score"] / abs(max_score)
                normalized_sum += normalized_score
                valid_map_count += 1

            if valid_map_count > 0:
                per_game_sums.append(normalized_sum / valid_map_count)

        if per_game_sums:
            total_average = sum(per_game_sums) / len(per_game_sums)
        else:
            total_average = 0.0

        player_id_score_sum[player_id] = total_average * 100.0

    return player_id_score_sum


# --- Markdown Generation Function ---


def create_leaderboard_markdown(player_scores: PlayerScores) -> str:
    """
    Generates a Markdown table string from a dictionary of player scores.
    """
    if not player_scores:
        return "No scores to display."

    sorted_players = sorted(
        player_scores.items(), key=lambda item: item[1], reverse=True
    )

    header = "| Rank | Player ID | Score |"
    separator = "|:----:|:----------|------:|"
    rows = []

    for rank, (player_id, score) in enumerate(sorted_players, 1):
        formatted_score = f"{score:.2f}"
        rows.append(f"| {rank} | {player_id} | {formatted_score} |")

    full_table = "\n".join([header, separator] + rows)
    return full_table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process XENT benchmark results and generate a Markdown leaderboard."
    )
    parser.add_argument(
        "input_file", type=Path, help="Path to the benchmark results JSON file."
    )
    parser.add_argument(
        "-o",
        "--output_file",
        type=Path,
        default="leaderboard.md",
        help="Path to write the output Markdown file (default: leaderboard.md).",
    )
    args = parser.parse_args()

    with args.input_file.open("r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    # --- 2. Process data to get player scores ---
    game_map_max_scores = compute_game_map_max_scores(benchmark_data)
    grouped_data = group_game_results_by_player_and_game(benchmark_data)
    player_scores = get_player_id_score_sum(grouped_data, game_map_max_scores)

    # --- 3. Generate the Markdown table ---
    markdown_output = create_leaderboard_markdown(player_scores)

    # --- 4. Print and write the output ---
    print("--- Generated Markdown Leaderboard ---")
    print(markdown_output)

    try:
        with args.output_file.open("w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"\nSuccessfully wrote leaderboard to '{args.output_file}'")
    except OSError as e:
        print(f"\nError writing to output file: {e}")
