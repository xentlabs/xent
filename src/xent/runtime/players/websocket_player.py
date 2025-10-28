import json
import logging
from collections.abc import Mapping
from typing import Any, Self, TypedDict

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xent.common.errors import XentApiError, XentConfigurationError, XentInternalError
from xent.common.util import dumps
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import TokenUsage, XentEvent
from xent.runtime.players.base_player import XGP, MoveResult
from xent.runtime.players.default_players import get_presentation_function


class WebsocketXGPOptions(TypedDict):
    websocket: Any


def check_websocket_xgp_options(options: PlayerOptions | None) -> WebsocketXGPOptions:
    if options is None:
        raise XentConfigurationError(
            "Player options for websocket player type cannot be None. Please provide valid options."
        )
    websocket = options.get("websocket")
    if websocket is None:
        raise XentConfigurationError("No websocket set for websocket player options")
    return {"websocket": websocket}


class WebsocketXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: PlayerOptions | None,
        executable_game_map: ExecutableGameMap,
    ):
        super().__init__(name, id, options, executable_game_map)
        self.event_history: list[XentEvent] = []
        self.presentation_function = get_presentation_function(executable_game_map)
        validated_options = check_websocket_xgp_options(options)
        self.websocket = validated_options["websocket"]

    def serialize(self) -> dict[str, Any]:
        raise XentInternalError("Serde not currently implemented for Websocket XGP")

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        raise XentInternalError("Serde not currently implemented for Websocket XGP")

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        # `post` for elicit request is made first. So the web client already knows that
        # it needs to make a move. Just wait for the next websocket input.
        move = await self._wait_for_websocket_input()
        return MoveResult(move, TokenUsage(input_tokens=0, output_tokens=0), [], "")

    async def post(self, event: XentEvent) -> None:
        logging.info(f"Sending event to websocket: {event}")
        self.event_history.append(event)
        await self._send_xent_event_to_websocket(event)

    async def _send_xent_event_to_websocket(self, event: XentEvent) -> None:
        try:
            print(f"Serializing: {event['type']}")
            print(f"Serializing: {event}")
            serialized_data = dumps({"type": "xent_event", "event": event})
            await self.websocket.send_text(serialized_data)
        except Exception as e:
            logging.error(f"Failed to send event to websocket: {e}")
            raise XentApiError("Failed to send event to websocket", "websocket") from e

    async def _wait_for_websocket_input(self) -> str:
        try:
            while True:
                data = await self.websocket.receive_text()
                message = json.loads(data)

                logging.info(f"Received websocket message: {message}")

                if not isinstance(message, dict) or "type" not in message:
                    logging.error("Invalid message format received")
                    continue

                if message["type"] == "xent_input":
                    input_text = message.get("input", "")
                    logging.info(f"Received user input: {input_text}")
                    return input_text
                else:
                    logging.info(f"Received non-input message: {message['type']}")
                    continue

        except Exception as e:
            logging.error(f"Websocket error while waiting for input: {e}")
            raise XentInternalError("Websocket error while waiting for input") from e
