import logging
from collections.abc import Mapping

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import TokenUsage, XentEvent
from xent.runtime.base_player import XGP, MoveResult
from xent.runtime.default_players import get_presentation_function


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
        self.metadata = executable_game_map["metadata"]

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        print("************************************************")
        message = self.presentation_function(
            register_states, self.event_history, self.metadata
        )
        print(message)
        print("************************************************")
        move = input(
            "You don't have to actually use <move></move> tags since you are a human player. Enter your move: "
        )
        return MoveResult(move, TokenUsage(input_tokens=0, output_tokens=0), [], "")

    async def post(self, event: XentEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)
