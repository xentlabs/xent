import argparse
import json
from typing import Any


def process_benchmark_results(
    benchmark_result: dict[str, Any], summary_only: bool = False
) -> dict[str, dict[str, list[tuple[str, float]]]]:
    processed_data: dict[str, dict[str, list[tuple[str, float]]]] = {}

    for game_result in benchmark_result["game_results"]:
        game_name = game_result["game"]["game"]["name"]
        map_seed = game_result["game"]["map_seed"]
        game_id = f"{game_name}-{map_seed}"

        # Assuming 1 player per XentGameResult as per the prompt
        player_config = game_result["game"]["players"][0]
        player_id = player_config["id"]
        player_name = player_config["name"]

        game_code = game_result["game"]["game"]["code"]

        if game_id not in processed_data:
            processed_data[game_id] = {}
            # Add game code entry
            processed_data[game_id]["CODE"] = [(game_code, 0.0)]

        if player_id not in processed_data[game_id]:
            if summary_only:
                processed_data[game_id][player_id] = [
                    ("", -1.0)
                ]  # Initialize with a low score
            else:
                processed_data[game_id][player_id] = []

        for iteration_result in game_result["game_results"]:
            elicit_response = None
            for event in iteration_result["xrt_history"]:
                if event["type"] == "elicit_response":
                    elicit_response = event["response"]
                    break  # Assuming only one elicit_response per iteration for simplicity, or taking the first one

            # Extract score for the current player using player_name
            score = iteration_result["scores"].get(player_name)

            if elicit_response is not None and score is not None:
                if summary_only:
                    current_best_elicit, current_best_score = processed_data[game_id][
                        player_id
                    ][0]
                    if score > current_best_score:
                        processed_data[game_id][player_id][0] = (elicit_response, score)
                else:
                    processed_data[game_id][player_id].append((elicit_response, score))

    return processed_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process benchmark results.")
    parser.add_argument("file_path", help="Path to the benchmark result JSON file.")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display only the highest score for each game and player.",
    )
    args = parser.parse_args()

    file_path = args.file_path
    summary_only = args.summary

    try:
        with open(file_path) as f:
            example_benchmark_result = json.load(f)

        output = process_benchmark_results(example_benchmark_result, summary_only)
        print(json.dumps(output, indent=2))

    except FileNotFoundError:
        print(f"Error: '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Check file format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
