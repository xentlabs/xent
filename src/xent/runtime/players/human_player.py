import logging
from collections.abc import Mapping
from typing import Any, Self

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import (
    LLMMessage,
    TokenUsage,
    XentEvent,
    deserialize_event,
    serialize_event,
)
from xent.runtime.players.base_player import XGP, MoveResult
from xent.runtime.players.default_players import get_presentation_function


class HumanXGP(XGP):
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
        self.presentation_ctx: dict[str, object] = {}
        self.conversation: list[LLMMessage] = []

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "player_type": "human",
            "options": self.options,
            "executable_game_map": self.executable_game_map,
            "event_history": [serialize_event(e) for e in self.event_history],
            "conversation": self.conversation,
            "presentation_ctx": self.presentation_ctx,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        human_xgp = cls(
            data["name"],
            data["id"],
            data["options"],
            data["executable_game_map"],
        )
        human_xgp.event_history = [deserialize_event(e) for e in data["event_history"]]
        human_xgp.presentation_ctx = data["presentation_ctx"]
        human_xgp.conversation = data["conversation"]
        return human_xgp

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        # Compute since_events: from after previous elicit_request up to and including current elicit_request
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

        # Append turn messages to conversation and pretty print for human
        if messages:
            self.conversation.extend(messages)

        print("************************************************")
        for message in self.conversation:
            print("---------------------------------------------")
            print(f"Role: {message['role']}")
            print(message["content"])
        print("************************************************")

        move = input(
            "You don't have to actually use <move></move> tags since you are a human player. Enter your move: "
        )

        # Append the human's response as an assistant message to preserve chat continuity
        self.conversation.append(LLMMessage(role="assistant", content=move))

        return MoveResult(
            move, TokenUsage(input_tokens=0, output_tokens=0), self.conversation, ""
        )

    async def post(self, event: XentEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)
