import json
import logging
from typing import Any

from xega.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xega.common.token_xent_list import TokenXentList
from xega.common.x_string import XString
from xega.common.xega_event import TokenUsage, XegaEvent
from xega.runtime.base_player import XGP
from xega.runtime.default_players import get_presentation_function


class XEncoder(json.JSONEncoder):
    """Custom JSON encoder for Xega types"""
    def default(self, o):
        if isinstance(o, XString):
            return str(o)
        elif isinstance(o, tuple):
            return list(o)
        elif isinstance(o, TokenXentList):
            scale = o.scale
            return [[pair[0], pair[1] * scale] for pair in o.pairs]
        return super().default(o)


def dumps(obj, **kwargs):
    """Helper function to encode objects with XEncoder"""
    return json.dumps(obj, cls=XEncoder, **kwargs)


class WebsocketXGP(XGP):
    """WebSocket-based human player for interactive web gameplay"""
    
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: PlayerOptions | None,
        executable_game_map: ExecutableGameMap,
    ):
        super().__init__(name, id, options, executable_game_map)
        self.event_history: list[XegaEvent] = []
        self.presentation_function = get_presentation_function(executable_game_map)
        
        # Get websocket from options
        if options is None:
            raise ValueError("WebsocketXGP requires 'websocket' in options")
        self.websocket: Any = options.get("websocket")
        if self.websocket is None:
            raise ValueError("WebsocketXGP requires 'websocket' in options")

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: dict[str, XString]
    ) -> tuple[str, TokenUsage]:
        """Request input from the web client and wait for response"""
        # Send elicit_request event to inform client about the input request
        # This is handled by the post() method when the runtime calls it
        
        # Wait for client input
        move = await self._wait_for_websocket_input()
        return move, TokenUsage(input_tokens=0, output_tokens=0)

    async def post(self, event: XegaEvent) -> None:
        """Send game events to the web client"""
        logging.info(f"Sending event to websocket: {event}")
        self.event_history.append(event)
        await self._send_xega_event_to_websocket(event)

    async def _send_xega_event_to_websocket(self, event: XegaEvent) -> None:
        """Send a Xega event over the websocket connection"""
        try:
            serialized_data = dumps({"type": "xega_event", "event": event})
            await self.websocket.send_text(serialized_data)
        except Exception as e:
            logging.error(f"Failed to send event to websocket: {e}")
            raise

    async def _wait_for_websocket_input(self) -> str:
        """Wait for user input from the websocket connection"""
        try:
            while True:
                data = await self.websocket.receive_text()
                message = json.loads(data)
                
                logging.info(f"Received websocket message: {message}")
                
                if not isinstance(message, dict) or "type" not in message:
                    logging.error("Invalid message format received")
                    continue
                    
                if message["type"] == "xega_input":
                    input_text = message.get("input", "")
                    logging.info(f"Received user input: {input_text}")
                    return input_text
                else:
                    logging.info(f"Received non-input message: {message['type']}")
                    continue
                    
        except Exception as e:
            logging.error(f"Websocket error while waiting for input: {e}")
            return ""