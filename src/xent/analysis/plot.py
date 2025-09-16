import json
import logging
import os
import re
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

from xent.common.configuration_types import BenchmarkResult, GameMapResults


def sanitize_filename(filename: str) -> str:
    """Removes or replaces characters problematic for filenames."""
    sanitized = re.sub(r"[^\w\-]+", "_", filename)
    sanitized = sanitized.strip("_")
    if not sanitized:
        return "unnamed_plot"
    return sanitized


def group_results_by_game_and_seed(
    benchmark_result: BenchmarkResult,
) -> dict[str, dict[str, list[GameMapResults]]]:
    """
    Group game results by game name and map seed.
    Returns: {game_name: {map_seed: [results]}}
    """
    grouped: dict[str, dict[str, list[GameMapResults]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for result in benchmark_result["results"]:
        game_name = result["game_map"]["name"]
        map_seed = result["game_map"]["map_seed"]
        grouped[game_name][map_seed].append(result)

    return grouped


def calculate_arms_values(
    results_by_seed: dict[str, list[GameMapResults]], player_id: str
) -> list[float]:
    """
    Calculate Average Running Max Score (ARMS) for a specific player across all map seeds.
    Returns a list of ARMS values, one for each iteration.
    """
    # Collect running max scores for each seed
    seed_running_maxes = []
    max_iterations = 0

    for _map_seed, seed_results in results_by_seed.items():
        # Find results for this player
        player_results = None
        for result in seed_results:
            if result["player"]["id"] == player_id:
                player_results = result
                break

        if player_results is None or not player_results["round_results"]:
            continue

        # Calculate running max for this seed
        running_max = float("-inf")
        seed_maxes = []

        for iteration_result in player_results["round_results"]:
            score = iteration_result["score"]
            running_max = max(running_max, score)
            seed_maxes.append(running_max)

        seed_running_maxes.append(seed_maxes)
        max_iterations = max(max_iterations, len(seed_maxes))

    if not seed_running_maxes:
        return []

    # Calculate average across seeds for each iteration
    arms_values = []
    for i in range(max_iterations):
        values_at_iteration = []
        for seed_maxes in seed_running_maxes:
            if i < len(seed_maxes):
                values_at_iteration.append(seed_maxes[i])

        if values_at_iteration:
            arms_values.append(np.mean(values_at_iteration).item())

    return arms_values


def generate_per_seed_plots(benchmark_result: BenchmarkResult, output_dir: str):
    """Generate score vs iteration plots for each game+seed combination."""
    logging.info(f"Generating per-seed plots in directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    grouped_results = group_results_by_game_and_seed(benchmark_result)

    for game_name, seed_results in grouped_results.items():
        for map_seed, results_list in seed_results.items():
            logging.info(
                f"  Generating plot for game: {game_name}, seed: {map_seed}..."
            )
            fig, ax = plt.subplots(figsize=(12, 7))

            plot_has_data = False
            for single_player_results in results_list:
                player_config = single_player_results["player"]
                player_id = player_config["id"]

                iteration_scores = [
                    res["score"] for res in single_player_results["round_results"]
                ]

                if not iteration_scores:
                    logging.info(
                        f"    Skipping player '{player_id}' - no iteration results found."
                    )
                    continue

                iterations = range(len(iteration_scores))

                ax.plot(
                    iterations,
                    iteration_scores,
                    marker="o",
                    linestyle="-",
                    markersize=4,
                    label=player_id,
                )
                plot_has_data = True
                logging.info(
                    f"    Added line for player: {player_id} ({len(iteration_scores)} iterations)"
                )

            if plot_has_data:
                ax.set_title(
                    f"Score vs. Iteration for Game: {game_name} (Seed: {map_seed})"
                )
                ax.set_xlabel("Iteration Number")
                ax.set_ylabel("Score")
                ax.grid(True, linestyle="--", alpha=0.6)
                ax.legend()

                safe_game_name = sanitize_filename(game_name)
                safe_seed = sanitize_filename(str(map_seed))
                output_filename = (
                    f"{safe_game_name}_seed_{safe_seed}_score_vs_iteration.png"
                )
                output_path = os.path.join(output_dir, output_filename)

                try:
                    fig.savefig(output_path, bbox_inches="tight")
                    logging.info(f"    Plot saved to: {output_path}")
                except Exception as e:
                    logging.info(f"    ERROR saving plot {output_path}: {e}")
            else:
                logging.info(
                    f"    No data plotted for game '{game_name}' seed '{map_seed}', skipping plot generation."
                )

            plt.close(fig)


def generate_aggregated_plots(benchmark_result: BenchmarkResult, output_dir: str):
    """Generate averaged score vs iteration plots across all seeds for each game."""
    logging.info(f"Generating aggregated plots in directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    grouped_results = group_results_by_game_and_seed(benchmark_result)

    for game_name, seed_results in grouped_results.items():
        logging.info(f"  Generating aggregated plot for game: {game_name}...")
        fig, ax = plt.subplots(figsize=(12, 7))

        # Collect all unique player IDs
        player_ids = set()
        for seed_data in seed_results.values():
            for result in seed_data:
                player_ids.add(result["player"]["id"])

        plot_has_data = False
        for player_id in sorted(player_ids):
            # Collect scores across all seeds for this player
            all_iteration_scores = []
            max_iterations = 0

            for seed_data in seed_results.values():
                for result in seed_data:
                    if result["player"]["id"] == player_id:
                        iteration_scores = [
                            res["score"] for res in result["round_results"]
                        ]
                        all_iteration_scores.append(iteration_scores)
                        max_iterations = max(max_iterations, len(iteration_scores))
                        break

            if not all_iteration_scores:
                continue

            # Calculate average scores at each iteration
            avg_scores = []
            for i in range(max_iterations):
                scores_at_iteration = []
                for scores in all_iteration_scores:
                    if i < len(scores):
                        scores_at_iteration.append(scores[i])

                if scores_at_iteration:
                    avg_scores.append(np.mean(scores_at_iteration))

            if avg_scores:
                iterations = range(len(avg_scores))
                ax.plot(
                    iterations,
                    avg_scores,
                    marker="o",
                    linestyle="-",
                    markersize=4,
                    label=player_id,
                )
                plot_has_data = True
                logging.info(
                    f"    Added averaged line for player: {player_id} ({len(avg_scores)} iterations)"
                )

        if plot_has_data:
            ax.set_title(
                f"Score vs. Iteration for Game: {game_name} (Averaged Across Seeds)"
            )
            ax.set_xlabel("Iteration Number")
            ax.set_ylabel("Average Score")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend()

            safe_filename = sanitize_filename(game_name)
            output_filename = f"{safe_filename}_score_vs_iteration.png"
            output_path = os.path.join(output_dir, output_filename)

            try:
                fig.savefig(output_path, bbox_inches="tight")
                logging.info(f"    Aggregated plot saved to: {output_path}")
            except Exception as e:
                logging.info(f"    ERROR saving aggregated plot {output_path}: {e}")
        else:
            logging.info(
                f"    No data plotted for aggregated game '{game_name}', skipping plot generation."
            )

        plt.close(fig)


def generate_arms_plots(benchmark_result: BenchmarkResult, output_dir: str):
    """Generate ARMS (Average Running Max Score) plots for each game."""
    logging.info(f"Generating ARMS plots in directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    grouped_results = group_results_by_game_and_seed(benchmark_result)

    for game_name, seed_results in grouped_results.items():
        logging.info(f"  Generating ARMS plot for game: {game_name}...")
        fig, ax = plt.subplots(figsize=(12, 7))

        # Collect all unique player IDs
        player_ids = set()
        for seed_data in seed_results.values():
            for result in seed_data:
                player_ids.add(result["player"]["id"])

        plot_has_data = False
        for player_id in sorted(player_ids):
            arms_values = calculate_arms_values(seed_results, player_id)

            if arms_values:
                iterations = range(len(arms_values))
                ax.plot(
                    iterations,
                    arms_values,
                    marker="o",
                    linestyle="-",
                    markersize=4,
                    label=player_id,
                )
                plot_has_data = True
                logging.info(
                    f"    Added ARMS line for player: {player_id} ({len(arms_values)} iterations)"
                )

        if plot_has_data:
            ax.set_title(f"Average Running Max Score (ARMS) for Game: {game_name}")
            ax.set_xlabel("Iteration Number")
            ax.set_ylabel("ARMS")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend()

            safe_filename = sanitize_filename(game_name)
            output_filename = f"{safe_filename}_arms.png"
            output_path = os.path.join(output_dir, output_filename)

            try:
                fig.savefig(output_path, bbox_inches="tight")
                logging.info(f"    ARMS plot saved to: {output_path}")
            except Exception as e:
                logging.info(f"    ERROR saving ARMS plot {output_path}: {e}")
        else:
            logging.info(
                f"    No data plotted for ARMS game '{game_name}', skipping plot generation."
            )

        plt.close(fig)


def generate_normalized_score_summary_chart(
    benchmark_result: BenchmarkResult, output_dir: str
):
    """Generate summary chart with scores averaged across map seeds."""
    logging.info(f"Generating summary chart in directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    scores_by_game_player: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    all_game_names = set()
    all_player_ids = set()

    # Collect all scores grouped by game and player
    for game_res in benchmark_result["results"]:
        if game_res["round_results"] is None or not game_res["round_results"]:
            continue
        game_name = game_res["game_map"]["name"]
        player_config = game_res["player"]
        normalized_score = game_res["score"]

        player_id = player_config["id"]
        all_game_names.add(game_name)
        all_player_ids.add(player_id)

        scores_by_game_player[game_name][player_id].append(normalized_score)

    if not all_game_names or not all_player_ids:
        logging.info("  No suitable data found to generate summary chart.")
        return

    ordered_game_names = sorted(list(all_game_names))
    ordered_player_ids = sorted(list(all_player_ids))
    num_games = len(ordered_game_names)
    num_players = len(ordered_player_ids)

    logging.info(
        f"  Found {num_games} games and {num_players} players for summary chart."
    )

    x = np.arange(num_games)
    total_width_per_cluster = 0.8
    bar_width = total_width_per_cluster / num_players
    first_bar_offset = -(total_width_per_cluster / 2) + (bar_width / 2)

    fig, ax = plt.subplots(figsize=(max(10, num_games * num_players * 0.5), 7))

    for i, player_id in enumerate(ordered_player_ids):
        player_scores = []
        for game in ordered_game_names:
            scores = scores_by_game_player.get(game, {}).get(player_id, [])
            if scores:
                player_scores.append(np.mean(scores).item())
            else:
                player_scores.append(0.0)

        bar_positions = x + first_bar_offset + i * bar_width

        rects = ax.bar(bar_positions, player_scores, bar_width, label=player_id)
        ax.bar_label(rects, padding=3, fmt="%.2f", fontsize=8)

    ax.set_ylabel("Average Normalized Score")
    ax.set_title(
        f"Average Normalized Score by Game and Player (Benchmark: {benchmark_result['expanded_config']['metadata']['benchmark_id']})"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(ordered_game_names)
    ax.legend(title="Players", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)

    if num_games > 5:
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")

    fig.tight_layout(rect=(0.0, 0.0, 0.9, 1.0))

    output_filename = f"benchmark_{benchmark_result['expanded_config']['metadata']['benchmark_id']}_normalized_score_summary.png"
    output_path = os.path.join(output_dir, output_filename)

    try:
        fig.savefig(output_path)
        logging.info(f"  Summary chart saved to: {output_path}")
    except Exception as e:
        logging.info(f"  ERROR saving summary chart {output_path}: {e}")

    plt.close(fig)


def generate_score_iteration_plots(benchmark_result: BenchmarkResult, output_dir: str):
    """
    Legacy function maintained for compatibility.
    Generates all types of plots: per-seed, aggregated, and ARMS.
    """
    generate_per_seed_plots(benchmark_result, output_dir)
    generate_aggregated_plots(benchmark_result, output_dir)
    generate_arms_plots(benchmark_result, output_dir)


def load_benchmark_result_from_json(file_path: str) -> BenchmarkResult:
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logging.info(f"Error: File not found at {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.info(f"Error: Invalid JSON format in file {file_path}: {e}")
        raise
    except Exception as e:
        logging.info(f"An unexpected error occurred while reading {file_path}: {e}")
        raise
