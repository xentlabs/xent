import base64
import logging
import os
import subprocess
from collections import defaultdict
from datetime import datetime

from xent.common.configuration_types import (
    BenchmarkResult,
    GameMapResults,
    GameMapRoundResult,
)
from xent.common.util import dumps, loads


def encode_image_to_base64(image_path: str) -> str:
    """Convert an image file to a base64 encoded string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def get_file_extension(image_path: str) -> str:
    """Get the file extension from a path."""
    return os.path.splitext(image_path)[1][1:]


def calculate_arms(game_results: list[GameMapRoundResult]) -> list[float]:
    """
    Calculate Average Running Max Score (ARMS) for a set of game iterations.
    Returns a list of ARMS values, one for each iteration.
    """
    if not game_results:
        return []

    arms_values = []
    running_max = float("-inf")

    for _i, iteration_result in enumerate(game_results):
        # Get the score for the black player (or adjust as needed)
        score = iteration_result["score"]
        running_max = max(running_max, score)

        # Calculate average of all running maxes up to this point
        # For now, just using the current running max
        # This could be extended to average across multiple metrics
        arms_values.append(running_max)

    return arms_values


def group_results_by_game_and_seed(
    game_results: list[GameMapResults],
) -> dict[str, dict[str, list[GameMapResults]]]:
    """
    Group game results by game name and map seed.
    Returns: {game_name: {map_seed: [results]}}
    """
    grouped: dict[str, dict[str, list[GameMapResults]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for result in game_results:
        game_name = result["game_map"]["name"]
        map_seed = result["game_map"]["map_seed"]
        grouped[game_name][map_seed].append(result)

    return grouped


def calculate_average_scores_across_seeds(
    results_by_seed: dict[str, list[GameMapResults]],
) -> dict[str, float]:
    """
    Calculate average scores across all map seeds for each player.
    Returns: {map_seed: {player_name: score}}
    """
    all_scores: dict[str, list[float]] = defaultdict(list)

    for _map_seed, results in results_by_seed.items():
        for result in results:
            player_id = result["player"]["id"]
            all_scores[player_id].append(result["score"])

    # Calculate averages
    average_scores = {}
    for player_id, player_scores in all_scores.items():
        avg_score = 0.0
        count = 0
        for score in player_scores:
            avg_score += score
            count += 1

        if count > 0:
            average_scores[player_id] = avg_score / count
        else:
            average_scores[player_id] = 0

    return average_scores


def generate_markdown_report(
    benchmark_result: BenchmarkResult,
    results_dir: str,
    output_file_name: str = "report.md",
) -> None:
    benchmark_id = benchmark_result["expanded_config"]["metadata"]["benchmark_id"]
    summary_image = f"benchmark_{benchmark_id}_normalized_score_summary.png"
    summary_image_path = os.path.join(results_dir, summary_image)

    markdown_content = []

    # Header
    markdown_content.append("---")
    markdown_content.append("title: 'AI Game Experiment Results'")
    markdown_content.append(f"date: '{datetime.now().strftime('%Y-%m-%d %H:%M')}'")
    markdown_content.append(f"subtitle: 'Benchmark ID: {benchmark_id}'")
    markdown_content.append("header-includes:")
    markdown_content.append("  - \\usepackage{float}")
    markdown_content.append("  - \\floatplacement{figure}{H}")
    markdown_content.append("---")
    markdown_content.append("")

    markdown_content.append("# AI Game Experiment Results\n")
    markdown_content.append(f"**Benchmark ID:** {benchmark_id}\n")
    markdown_content.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Overall results image
    if os.path.exists(summary_image_path):
        markdown_content.append("\n## Overall Results\n")
        markdown_content.append("")
        if output_file_name.endswith(".md"):
            markdown_content.append(f"![Overall Results]({summary_image})")
        else:
            encoded_img = encode_image_to_base64(summary_image_path)
            img_ext = get_file_extension(summary_image_path)
            markdown_content.append(
                f'<img src="data:image/{img_ext};base64,{encoded_img}" alt="Overall Results" style="max-width:100%;">'
            )
    markdown_content.append("")

    # Group results by game and map seed
    grouped_results = group_results_by_game_and_seed(benchmark_result["results"])

    # Extract player IDs and game configurations
    player_ids = set()
    game_configs = {}
    map_seeds_per_game = {}

    for game_name, seed_results in grouped_results.items():
        map_seeds_per_game[game_name] = len(seed_results)

        for results in seed_results.values():
            if results:
                game_config = results[0]["game_map"]
                game_configs[game_name] = game_config

                player_ids.add(results[0]["player"]["id"])

    sorted_player_ids = sorted(list(player_ids))

    # Verify all games have the same number of map seeds
    unique_seed_counts = set(map_seeds_per_game.values())
    if len(unique_seed_counts) > 1:
        raise ValueError(
            f"Not all games have the same number of map seeds: {map_seeds_per_game}"
        )

    num_map_seeds = list(unique_seed_counts)[0] if unique_seed_counts else 0

    # Score Summary Table (averaged across map seeds)
    markdown_content.append("\n## Score Summary (Averaged Across Map Seeds)\n")
    markdown_content.append(f"\n*Number of map seeds per game: {num_map_seeds}*\n")

    table_header = "| Game Name |"
    for player_id in sorted_player_ids:
        table_header += f" {player_id} |"
    markdown_content.append(table_header)

    table_separator = "|" + "---|" * (len(sorted_player_ids) + 1)
    markdown_content.append(table_separator)

    # Calculate average scores for each game
    for game_name in sorted(grouped_results.keys()):
        row = f"| {game_name} |"

        # Calculate average scores across all map seeds
        average_scores = calculate_average_scores_across_seeds(
            grouped_results[game_name]
        )

        for player_id in sorted_player_ids:
            if player_id in average_scores:
                row += f" {average_scores[player_id]:.4f} |"
            else:
                row += " N/A |"

        markdown_content.append(row)

    # Detailed Game Results
    markdown_content.append("\n## Detailed Game Results\n")

    for game_name in sorted(grouped_results.keys()):
        game_config = game_configs[game_name]
        markdown_content.append(f"\n### Game: {game_name}\n")

        # Game Code
        markdown_content.append("#### Game Code\n")
        markdown_content.append("```python")
        markdown_content.append(game_config["code"])
        markdown_content.append("```\n")

        # Game Configuration
        markdown_content.append("#### Game Configuration\n")
        markdown_content.append("```json")

        config_for_display = loads(dumps(game_config))
        if "game" in config_for_display and "code" in config_for_display["game"]:
            del config_for_display["game"]["code"]

        markdown_content.append(dumps(config_for_display, indent=2))
        markdown_content.append("```\n")

        # Aggregated Results Section
        markdown_content.append("#### Aggregated Results (Across All Map Seeds)\n")

        # ARMS Plot
        arms_image = f"{game_name}_arms.png"
        arms_image_path = os.path.join(results_dir, arms_image)

        if os.path.exists(arms_image_path):
            markdown_content.append("##### Average Running Max Score (ARMS)\n")
            if output_file_name.endswith(".md"):
                markdown_content.append(f"![ARMS for {game_name}]({arms_image})")
            else:
                encoded_img = encode_image_to_base64(arms_image_path)
                img_ext = get_file_extension(arms_image_path)
                markdown_content.append(
                    f'<img src="data:image/{img_ext};base64,{encoded_img}" alt="ARMS for {game_name}" style="max-width:100%;">'
                )
            markdown_content.append("")

        # Aggregated Score vs Iteration Plot
        agg_iteration_image = f"{game_name}_score_vs_iteration.png"
        agg_iteration_image_path = os.path.join(results_dir, agg_iteration_image)

        if os.path.exists(agg_iteration_image_path):
            markdown_content.append("##### Score vs Iteration (Averaged)\n")
            if output_file_name.endswith(".md"):
                markdown_content.append(
                    f"![Score vs Iteration for {game_name}]({agg_iteration_image})"
                )
            else:
                encoded_img = encode_image_to_base64(agg_iteration_image_path)
                img_ext = get_file_extension(agg_iteration_image_path)
                markdown_content.append(
                    f'<img src="data:image/{img_ext};base64,{encoded_img}" alt="Score vs Iteration for {game_name}" style="max-width:100%;">'
                )
            markdown_content.append("")

        # Average Scores Table
        markdown_content.append("##### Average Player Scores\n")
        markdown_content.append("| Player | Average Score |")
        markdown_content.append("|--------|---------------|")

        average_scores = calculate_average_scores_across_seeds(
            grouped_results[game_name]
        )

        for player_id in sorted_player_ids:
            if player_id in average_scores:
                markdown_content.append(
                    f"| {player_id} | {average_scores[player_id]:.4f} |"
                )
            else:
                markdown_content.append(f"| {player_id} | N/A |")

        markdown_content.append("")

        # Results by Map Seed
        markdown_content.append("#### Results by Map Seed\n")

        for map_seed in sorted(grouped_results[game_name].keys()):
            markdown_content.append(f"\n##### Map Seed: {map_seed}\n")

            # Score vs Iteration Plot for this seed
            seed_iteration_image = f"{game_name}_seed_{map_seed}_score_vs_iteration.png"
            seed_iteration_image_path = os.path.join(results_dir, seed_iteration_image)

            if os.path.exists(seed_iteration_image_path):
                if output_file_name.endswith(".md"):
                    markdown_content.append(
                        f"![Score vs Iteration for {game_name} (Seed: {map_seed})]({seed_iteration_image})"
                    )
                else:
                    encoded_img = encode_image_to_base64(seed_iteration_image_path)
                    img_ext = get_file_extension(seed_iteration_image_path)
                    markdown_content.append(
                        f'<img src="data:image/{img_ext};base64,{encoded_img}" alt="Score vs Iteration for {game_name} (Seed: {map_seed})" style="max-width:100%;">'
                    )
                markdown_content.append("")

            # Player Scores for this seed
            markdown_content.append("| Player | Score (Player: black) |")
            markdown_content.append("|-------|-----------------------|")

            seed_result_list = grouped_results[game_name][map_seed]

            for player_id in sorted_player_ids:
                found = False
                for result in seed_result_list:
                    player = result["player"]
                    if player["id"] == player_id:
                        score = result["score"]
                        markdown_content.append(f"| {player_id} | {score:.4f} |")
                        break

                if not found:
                    markdown_content.append(f"| {player_id} | N/A |")

            markdown_content.append("")

        markdown_content.append("\n")

    # Write the report
    with open(os.path.join(results_dir, output_file_name), "w") as f:
        f.write("\n".join(markdown_content))

    logging.info(
        f"Report generated successfully: {os.path.join(results_dir, output_file_name)}"
    )


def generate_pdf(
    results_dir: str,
    markdown_file: str,
    output_pdf: str | None = None,
    pandoc_options: list[str] | None = None,
) -> str:
    """
    Generate a PDF from a markdown file using pandoc.

    Args:
        markdown_file: Path to the markdown file
        output_pdf: Path to the output PDF file (default: same name as markdown but with .pdf extension)
        pandoc_options: Additional options to pass to pandoc

    Returns:
        Path to the generated PDF file
    """
    if output_pdf is None:
        output_pdf = os.path.splitext(markdown_file)[0] + ".pdf"

    if pandoc_options is None:
        pandoc_options = []

    cmd = [
        "pandoc",
        markdown_file,
        "-o",
        output_pdf,
    ] + pandoc_options

    try:
        logging.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=results_dir)
        logging.info(f"PDF generated successfully: {output_pdf}")
        return output_pdf
    except subprocess.CalledProcessError as e:
        logging.info(f"Error generating PDF: {e}")
        logging.info(f"Pandoc stderr: {e.stderr}")
        raise
    except FileNotFoundError as e:
        logging.info(e)
        logging.info(
            "Error: pandoc not found. Please make sure it's installed and in your PATH."
        )
        logging.info("You can still generate the PDF manually by running:")
        logging.info(
            f"pandoc {markdown_file} -o {output_pdf} {' '.join(pandoc_options)}"
        )
        return markdown_file
