import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from xega.common.xega_types import XegaBenchmarkResult, XegaGameResult

PlayerId = str
GameName = str
PlayerScores = Dict[PlayerId, float]

GroupedData = Dict[PlayerId, Dict[GameName, List[XegaGameResult]]]


def group_game_results_by_player_and_game(
    benchmark_result: XegaBenchmarkResult,
) -> GroupedData:
    """
    Groups game results first by player ID and then by game name.
    """
    games_by_player: Dict[str, List[XegaGameResult]] = defaultdict(list)

    for game_result in benchmark_result.get("game_results", []):
        players = game_result.get("game", {}).get("players", [])
        if players:
            player_id = players[0].get("id")
            if player_id:
                games_by_player[player_id].append(game_result)

    result: GroupedData = {}
    for player_id, game_results in games_by_player.items():
        games_by_name: Dict[str, List[XegaGameResult]] = defaultdict(list)
        for game_result in game_results:
            game_name = game_result.get("game", {}).get("game", {}).get("name")
            if game_name:
                games_by_name[game_name].append(game_result)

        result[player_id] = dict(games_by_name)

    return result


def get_player_id_score_sum(grouped_data: GroupedData) -> PlayerScores:
    """
    Calculates the total score for each player across all their games.
    """
    player_id_score_sum: PlayerScores = {}

    for player_id, games in grouped_data.items():
        total_score = 0.0
        for game_results in games.values():
            for game_result in game_results:
                total_score += game_result.get("scores", {}).get("black", 0.0)

        player_id_score_sum[player_id] = total_score

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
        description="Process XEGA benchmark results and generate a Markdown leaderboard."
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
    grouped_data = group_game_results_by_player_and_game(benchmark_data)
    player_scores = get_player_id_score_sum(grouped_data)

    # --- 3. Generate the Markdown table ---
    markdown_output = create_leaderboard_markdown(player_scores)

    # --- 4. Print and write the output ---
    print("--- Generated Markdown Leaderboard ---")
    print(markdown_output)

    try:
        with args.output_file.open("w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"\nSuccessfully wrote leaderboard to '{args.output_file}'")
    except IOError as e:
        print(f"\nError writing to output file: {e}")
