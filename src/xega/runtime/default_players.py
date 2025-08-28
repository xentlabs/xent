import logging
import re

from xega.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
    TokenUsage,
)
from xega.common.util import dumps
from xega.common.x_string import XString
from xega.common.xega_event import XegaEvent
from xega.presentation.executor import PresentationFunction
from xega.runtime.base_player import XGP
from xega.runtime.llm_api_client import LLMMessage, make_client


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
        self.event_history: list[XegaEvent] = []
        self.token_usage_per_move = token_usage_per_move or {
            "input_tokens": 1,
            "output_tokens": 1,
        }

        self.presentation_function = get_presentation_function(executable_game_map)
        self.last_message_to_llm = ""

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: dict[str, XString]
    ) -> tuple[str, TokenUsage]:
        message = self.presentation_function(register_states, self.event_history)

        self.last_message_to_llm = message

        return ("mocked_move", self.token_usage_per_move.copy())

    async def post(self, event: XegaEvent) -> None:
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
        self.event_history: list[XegaEvent] = []
        self.conversation: list[LLMMessage] = []
        self.reminder_message: LLMMessage | None = None
        self.presentation_function = get_presentation_function(executable_game_map)

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(
        self, var_name: str, register_states: dict[str, XString]
    ) -> tuple[str, TokenUsage]:
        message = self.presentation_function(register_states, self.event_history)
        self.conversation = [LLMMessage(role="user", content=message)]

        logging.info("Sending message to LLM")
        logging.info(f"conversation: {dumps(self.conversation)}")
        reply, token_usage = await self.client.request(self.conversation)
        logging.info(f"Received response from LLM: {dumps(reply)}")
        reply = re.sub(r"<think>.*?</think>", "", reply or "", flags=re.DOTALL)

        move_matches = re.findall(r"<move>(.*?)</move>", reply, flags=re.DOTALL)
        if move_matches:
            result = move_matches[-1]
        else:
            self.reminder_message = LLMMessage(
                role="user",
                content="No move specified. Make sure that you provide your move within the <move></move> tags.",
            )
            result = reply
        logging.info(f"Parsed LLM move: {result}")
        return result, token_usage

    async def post(self, event: XegaEvent) -> None:
        self.event_history.append(event)


def get_presentation_function(
    executable_game_map: ExecutableGameMap,
) -> PresentationFunction:
    presentation_code = executable_game_map["game_map"]["presentation_function"]
    return PresentationFunction(presentation_code)
