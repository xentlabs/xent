import json
import sys
from typing import Dict, List, Tuple, Any

def process_benchmark_results(benchmark_result: Dict[str, Any]) -> Dict[str, Dict[str, List[Tuple[str, float]]]]:
    processed_data: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}

    for game_result in benchmark_result["game_results"]:
        game_name = game_result["game"]["game"]["name"]
        map_seed = game_result["game"]["map_seed"]
        game_id = f"{game_name}-{map_seed}"

        # Assuming 1 player per XegaGameResult as per the prompt
        player_config = game_result["game"]["players"][0]
        player_id = player_config["id"]
        player_name = player_config["name"]

        if game_id not in processed_data:
            processed_data[game_id] = {}
        if player_id not in processed_data[game_id]:
            processed_data[game_id][player_id] = []

        for iteration_result in game_result["game_results"]:
            elicit_response = None
            for event in iteration_result["xrt_history"]:
                if event["type"] == "elicit_response":
                    elicit_response = event["response"]
                    break # Assuming only one elicit_response per iteration for simplicity, or taking the first one

            # Extract score for the current player using player_name
            score = iteration_result["scores"].get(player_name)

            if elicit_response is not None and score is not None:
                processed_data[game_id][player_id].append((elicit_response, score))

    return processed_data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_benchmark_results.py <path_to_benchmark_result.json>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r") as f:
            example_benchmark_result = json.load(f)
        
        output = process_benchmark_results(example_benchmark_result)
        print(json.dumps(output, indent=2))

    except FileNotFoundError:
        print(f"Error: '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Check file format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")