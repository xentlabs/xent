import logging
import re
from collections.abc import Mapping
from typing import Any, Self

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xent.common.util import dumps
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import (
    LLMMessage,
    TokenUsage,
    XentEvent,
    deserialize_event,
    serialize_event,
)
from xent.presentation.executor import PresentationFunction
from xent.runtime.players.base_player import XGP, MoveResult
from xent.runtime.players.llm_api_client import make_client


class MockXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: PlayerOptions | None,
        executable_game_map: ExecutableGameMap,
        token_usage_per_move: TokenUsage | None = None,
    ):
        super().__init__(name, id, options, executable_game_map)
        self.event_history: list[XentEvent] = []
        self.token_usage_per_move = token_usage_per_move or {
            "input_tokens": 1,
            "output_tokens": 1,
        }
        self.presentation_function = get_presentation_function(executable_game_map)
        self.presentation_ctx: dict[str, object] = {}
        self.conversation: list[LLMMessage] = []

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "player_type": "mock",
            "options": self.options,
            "executable_game_map": self.executable_game_map,
            "token_usage_per_move": self.token_usage_per_move,
            "event_history": [serialize_event(e) for e in self.event_history],
            "presentation_ctx": self.presentation_ctx,
            "conversation": self.conversation,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        mock_xgp = cls(
            data["name"],
            data["id"],
            data["options"],
            data["executable_game_map"],
            data["token_usage_per_move"],
        )
        mock_xgp.event_history = [deserialize_event(e) for e in data["event_history"]]
        mock_xgp.presentation_ctx = data["presentation_ctx"]
        mock_xgp.conversation = data["conversation"]
        return mock_xgp

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        # Compute since_events based on last elicit_request
        elicit_idxs = [
            i
            for i, e in enumerate(self.event_history)
            if e.get("type") == "elicit_request"
        ]
        if not elicit_idxs:
            since_events: list[XentEvent] = list(self.event_history)
        else:
            start = elicit_idxs[-2] + 1 if len(elicit_idxs) > 1 else 0
            end = elicit_idxs[-1] + 1
            since_events = self.event_history[start:end]

        messages, self.presentation_ctx = self.presentation_function(
            register_states,
            since_events,
            self.metadata,
            full_history=self.event_history,
            ctx=self.presentation_ctx,
        )
        # Append the new messages to the conversation (append-only)
        self.conversation.extend(messages)

        return MoveResult(
            "mocked_move",
            self.token_usage_per_move.copy(),
            self.conversation,
            "full mocked_move",
        )

    async def post(self, event: XentEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)


class DefaultXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: PlayerOptions | None,
        executable_game_map: ExecutableGameMap,
    ):
        super().__init__(name, id, options, executable_game_map)
        self.client = make_client(options)
        self.game_code = executable_game_map["game_map"]["code"]
        self.event_history: list[XentEvent] = []
        self.conversation: list[LLMMessage] = []
        self.reminder_message: LLMMessage | None = None
        self.presentation_function = get_presentation_function(executable_game_map)
        self.presentation_ctx: dict[str, object] = {}

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "player_type": "default",
            "options": self.options,
            "executable_game_map": self.executable_game_map,
            "event_history": [serialize_event(e) for e in self.event_history],
            "conversation": self.conversation,
            "reminder_message": self.reminder_message,
            "presentation_ctx": self.presentation_ctx,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        default_xgp = cls(
            data["name"],
            data["id"],
            data["options"],
            data["executable_game_map"],
        )
        default_xgp.event_history = [
            deserialize_event(e) for e in data["event_history"]
        ]
        default_xgp.presentation_ctx = data["presentation_ctx"]
        default_xgp.conversation = data["conversation"]
        default_xgp.reminder_message = data["reminder_message"]
        return default_xgp

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        # Compute since_events as everything after previous elicit_request up to this elicit_request (inclusive)
        elicit_idxs = [
            i
            for i, e in enumerate(self.event_history)
            if e.get("type") == "elicit_request"
        ]
        if not elicit_idxs:
            since_events: list[XentEvent] = list(self.event_history)
        else:
            start = elicit_idxs[-2] + 1 if len(elicit_idxs) > 1 else 0
            end = elicit_idxs[-1] + 1
            since_events = self.event_history[start:end]

        messages, self.presentation_ctx = self.presentation_function(
            register_states,
            since_events,
            self.metadata,
            full_history=self.event_history,
            ctx=self.presentation_ctx,
        )

        # Append the new messages for this turn to the persistent conversation (append-only)
        if messages:
            self.conversation.extend(messages)

        logging.info("Sending message to LLM")
        logging.info(f"conversation: {dumps(self.conversation)}")
        full_reply, token_usage = await self.client.request(self.conversation)
        logging.info(f"Received response from LLM: {dumps(full_reply)}")
        reply = re.sub(r"<think>.*?</think>", "", full_reply or "", flags=re.DOTALL)

        # Append the assistant reply to the conversation
        self.conversation.append(LLMMessage(role="assistant", content=reply))

        move_matches = re.findall(r"<move>(.*?)</move>", reply, flags=re.DOTALL)
        if move_matches:
            result = move_matches[-1]
        else:
            reminder = LLMMessage(
                role="user",
                content="No move specified. Make sure that you provide your move within the <move></move> tags.",
            )
            # Append a reminder to the chat so next turn sees the guidance
            self.conversation.append(reminder)
            self.reminder_message = reminder
            result = reply
        logging.info(f"Parsed LLM move: {result}")
        return MoveResult(result, token_usage, self.conversation, reply)

    async def post(self, event: XentEvent) -> None:
        self.event_history.append(event)


def get_presentation_function(
    executable_game_map: ExecutableGameMap,
) -> PresentationFunction:
    presentation_code = executable_game_map["game_map"]["presentation_function"]
    return PresentationFunction(presentation_code)
