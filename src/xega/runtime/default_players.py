import logging
import re
from typing import List, Optional

from xega.common.errors import XegaInternalError
from xega.common.token_xent_list import round_xent
from xega.common.util import dumps
from xega.common.xega_types import PlayerName, PlayerOptions, XegaEvent, XegaGameConfig
from xega.runtime.base_player import XGP
from xega.runtime.llm_api_client import LLMMessage, make_client


class MockXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        super().__init__(name, id, options, game_config)
        self.history: List[str] = []
        self.event_history: List[XegaEvent] = []

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(self, var_name: str) -> str:
        return "mocked_move"

    async def post(self, event: XegaEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)
        self.history.append(event_to_message(event))


class DefaultXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        super().__init__(name, id, options, game_config)
        self.client = make_client(options)
        self.game_code = game_config["game"]["code"]
        self.event_history: List[XegaEvent] = []
        self.history: List[str] = []
        self.conversation: List[LLMMessage] = []
        self.reminder_message: LLMMessage | None = None

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(self, var_name: str) -> str:
        message = "The current game log lines are:\n" + "\n".join(self.history) + "\n"
        message += "What do you play? Answer your move within <move></move> tags"
        self.conversation = [
            LLMMessage(role="system", content=self.system_prompt()),
            LLMMessage(role="user", content=message),
        ]
        if self.reminder_message:
            self.conversation.append(self.reminder_message)

        logging.info("Sending message to LLM")
        logging.debug(f"conversation: {dumps(self.conversation)}")
        reply = await self.client.request(self.conversation)
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
        return result

    async def post(self, event: XegaEvent) -> None:
        self.event_history.append(event)
        self.history.append(event_to_message(event))

    def system_prompt(self) -> str:
        return get_system_prompt(self.game_code)


def get_system_prompt(game_code: str) -> str:
    prompt = f"""
You are playing a game described in a custom language. The game is based around the cross entropy of a judge model. Here is a brief overview of the language:

<game_language>
Each line of code starts with an instruction. Here are the most important instructions:

<instructions>
- `assign`: Each keyword argument name is a variable name, and the value is assigned to that variable.
- `reveal`: Reveal information to player, the arguments are the variables to reveal.
- `elicit`: Ask player for input. The arguments are the variables that will hold the result of the elicit. If there are multiple variables specified, then there will be one `elicit` performed for each. The final argument is the max number of tokens to elicit.
- `ensure`: Validate conditions. If a condition is not met, code execution jumps to the last executed `elicit` line.
- `reward`: Reward points. The arguments are the variables that hold the numerical score you will be rewarded.
</instructions>

Your goal is to maximize your score. Do this by making your rewards as large as possible.

When you receive an `elicit` request, you must respond with a move within `<move></move>` tags. Any other text in your response will be ignored.

The game code will have some comments that describe the game and some basic strategy. Here is the game you are playing:
<game_code>
{game_code}
</game_code>

Remember, you must respond to the `elicit` request with your move within `<move></move>` tags. Any other text in your response will be ignored. Use the game code and state to determine what text to provide such that it will maximize your score. Make sure your move is valid and will meet the conditions specified in the ensure statements in the game code.
"""
    return prompt


def event_to_message(event: XegaEvent) -> str:
    if event["type"] == "elicit_request":
        return f"{event["line_num"]:02d}-<elicit>: {event["var_name"]} (max {event["max_len"]} tokens)"
    elif event["type"] == "elicit_response":
        return f"{event["line_num"]:02d}-<elicit response>: {event["response"]}"
    elif event["type"] == "reveal":
        return f"{event["line_num"]:02d}-<reveal>: {str([f'{arg}: "{str(event['values'][arg])}' for arg in event['values']])}"
    elif event["type"] == "reward":
        return f"{event["line_num"]:02d}-<reward>: Total reward: {round_xent(event['value'].total_xent())}, per-token rewards: {str(event['value'])}"
    elif event["type"] == "failed_ensure":
        results = [
            f"Argument {i} result: {arg}"
            for i, arg in enumerate(event["ensure_results"])
        ]
        results_string = ", ".join(results)
        return f"{event["line_num"]:02d}-<ensure>: Failed ensure. {results_string}. Moving code execution to beacon: {event["beacon"]}"
    else:
        raise XegaInternalError(f"Unknown event type: {event["type"]}")
