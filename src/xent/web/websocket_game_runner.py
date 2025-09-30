import asyncio
import contextlib
import json
import logging
from typing import Any

from xent.benchmark.run_benchmark import run_game
from xent.common.configuration_types import (
    ExecutableGameMap,
    GameMapConfig,
    PlayerConfig,
    XentMetadata,
)
from xent.common.version import get_xent_version
from xent.runtime.judge import Judge


async def run_websocket_game(websocket: Any, game_code: str) -> None:
    try:
        metadata: XentMetadata = {
            "benchmark_id": "interactive_play",
            "xent_version": get_xent_version(),
            "judge_model": "gpt2",
            "num_rounds_per_game": 999,
            "seed": "websocket_game",
            "store_full_player_interactions": False,
        }

        player_config: PlayerConfig = {
            "name": "black",
            "id": "websocket_player",
            "player_type": "websocket",
            "options": {"websocket": websocket},
        }

        game_map_config: GameMapConfig = {
            "name": "Interactive Game",
            "code": game_code,
            "presentation_function": _get_default_presentation_function(),
            "map_seed": "interactive",
        }

        executable_game_map: ExecutableGameMap = {
            "metadata": metadata,
            "player": player_config,
            "game_map": game_map_config,
        }

        # Create judge
        judge = Judge(metadata["judge_model"])
        judge.set_seed(metadata["seed"], "")

        logging.info("Starting websocket game execution")

        # Run the game
        result = await run_game(
            executable_game_map=executable_game_map,
            judge=judge,
            raise_on_error=True,
        )

        if result:
            logging.info(f"Game completed successfully. Final score: {result['score']}")
        else:
            logging.warning("Game completed but returned no results")

    except asyncio.CancelledError:
        # Game was cancelled (user disconnected/navigated away)
        logging.info("Websocket game cancelled - user disconnected")
        raise  # Re-raise to properly handle cleanup
    except Exception as e:
        logging.error(f"Error running websocket game: {e}")
        with contextlib.suppress(Exception):
            await websocket.send_text(
                json.dumps({"type": "xent_error", "error": str(e)})
            )
        raise


def _get_default_presentation_function() -> str:
    """Get a simple default presentation function for websocket games"""
    return """def present(state, history, metadata):
    \"\"\"Default presentation function for websocket games\"\"\"
    output = []
    for event in history:
        if event['type'] == 'elicit_request':
            output.append(f"Input requested for variable: {event['var_name']}")
        elif event['type'] == 'elicit_response':
            output.append(f"You provided: {event['response']}")
        elif event['type'] == 'reveal':
            output.append(f"Revealed: {event['values']}")
        elif event['type'] == 'reward':
            output.append(f"Score: {event['value']}")
        elif event['type'] == 'failed_ensure':
            output.append(f"Failed ensure - moving to {event['beacon']}")
        else:
            output.append(f"Event: {event}")
    return '\\n'.join(output)"""
