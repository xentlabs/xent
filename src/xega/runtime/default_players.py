import logging
import re
from typing import List, Optional

from xega.common.errors import XegaInternalError
from xega.common.token_xent_list import round_xent
from xega.common.util import dumps
from xega.common.xega_types import (
    LLMMessage,
    PlayerName,
    PlayerOptions,
    XegaEvent,
    XegaGameConfig,
)
from xega.runtime.base_player import XGP
from xega.runtime.llm_api_client import make_client


class MockXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        super().__init__(name, options, game_config)
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

    def post(self, event: XegaEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)
        self.history.append(event_to_message(event))


class DefaultXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        super().__init__(name, options, game_config)
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

    def post(self, event: XegaEvent) -> None:
        logging.info(f"Player received message: {event}")
        self.event_history.append(event)
        self.history.append(event_to_message(event))

    def system_prompt(self) -> str:
        return get_system_prompt(
            self.name, self.game_code, self.game_config["num_variables_per_register"]
        )


def get_system_prompt(
    player_name: str, game_code: str, num_registers_per_type: int
) -> str:
    prompt = f"""
You are playing a game described in a custom language. You are playing as "{player_name}". Here is a brief overview of the language:

<game_language>
The game language is a simple python DSL that is structured as follows:

Each line of code starts with an instruction. Each instruction can have a number of arguments, which are either positional or keyword arguments. Here are the instructions:

<instructions>
- `assign`: Assign values to registers. Each keyword argument name is a variable name, and the value is assigned to that register. Assign only takes keyword arguments.
- `reveal`: Reveal information to a player. The first argument can be the player to which the data is revealed. If a player isn't specified, the default player is 'black'. The rest of the arguments are the data to reveal. Reveal only takes positional arguments.
- `elicit`: Ask player for input. The first argument can be the player asked. If a player isn't specified, the default player is 'black'. The subsequent arguments are registers that will hold the result of the elicit. If there are multiple variables specified, then there will be one `elicit` performed for each. The final argument is the max number of tokens to elicit. Elicit only takes positional arguments.
- `ensure`: Validate conditions. Each positional argument is a condition to validate and should evaluate to True or False. If conditions are all met, the code continues to the next line. If not, the code jumps to the last executed `elicit` line. The game allows for a maximum of 10 consecutive failures to meet an ensure before exiting. `Ensure` only takes positional arguments.
- `reward`: Reward a player. The first argument can be the player to reward. If a player isn't specified, the default player is 'black'. The rest of the arguments are numerical amounts to reward that player. Reward only takes positional arguments.
- `beacon`: Set a flag in the code to jump to. `beacon` only takes a single position argument, which is the flag object.
- `replay`: Jump to a previously set flag. The first argument is the flag to jump to. The second argument is the number of times to perform the jump. Once that count has been reached, `replay` will allow execution to continue to the next line.
</instructions>

In addition to the instructions, there are a number of functions defined in the game language. Here are the functions:
<functions>
- `story()`: Returns a string that contains a story from a corpus provided by the language
- `common_word_set(s1, s2)`: Returns a set of common words between two strings
- `first_n_tokens(s, n)`: Returns a string that is the first n tokens of `s`
- `remove_common_words(s1, s2)`: Returns a string that is `s1` with all common words with `s2` removed
- `xent(s1)`: Returns the summed cross entropy of a string with respect to the model
- `xent(s1 | s2)`: Returns the cross entropy of s1 when prefixed with s2. So this is basically xent(f"{{prefix}}{{s1}}") - xent(prefix).
- `nex`: A shorthand for `-1 * xent`
- `xed(s1 | s2)`: A shorthand to `xent(s1) - xent(s1 | s2)`. This is basically saying how much the prefix `s2` helps in predicting `s1`.
- `xed(s1 | s2, pre_prompt="abc")`: This is a special shorthand for `xent(s1 | pre_prompt) - xent(s1 | (pre_prompt + s2))`.
- `dex`: A shorthand for `-1 * xed`
</functions>

There are also a few special string operations defined:
<operations>
- `s1 + s2`: Concatenate two strings
- `s1 // s2`: the substring of `s1` that comes before the first occurrence of `s2` (does not include `s2`). If `s2` is not in `s1`, then `s1` is returned.
- `s1 % s2`: the substring of `s1` that comes after the first occurrence of `s2` (does not include `s2`). If `s2` is not in `s1`, then "" is returned.

By convention, we say that `s2` does not appear in `s1` if `s2` is the empty string. So `s1 // ""` is always `s1` and `s1 % ""` is always "".
</operations>

The game has a fixed number of registers for holding data. Registers only hold strings. Here are the registers:
<registers>
There are fixed sets of registers named: ["a", "b", "c", "s", "t", "x", "y", "p"]
There are {num_registers_per_type} registers per type. The names are in the format of "a", "a1", "a2", etc

There are three static register types: ["a", "b", "c"]. Static registers are not allowed to be modified.
There are three public register types: ["a", "b", "p"]. Public registers are visible to all players at all times.
</registers>

<flags>
The game has two flag objects defined: flag_1 and flag_2. These are used by `beacon` and `replay` calls to jump to a line of code.
</flags>

<players>
The game can be played by multiple players. Each player has a name. The players are: ["black", "white", "alice", "bob", "carol", "env"]

If a game is single-player, the default player is "black".

The players "black", "white", and "env" are omniscient players. They can see all registers at all times.

The players "black" and "white" are a zero-sum pair. Any reward given to one of these players is subtracted from the other.

The player "env" does not receive any rewards. It is used to provide a game environment for the other players.
</players>

</game_language>

You are playing as player "{player_name}". Your goal is to maximize your score, which is given to you as prescribed by the reward function.

When you receive an `elicit` request, you must respond with a move within `<move></move>` tags. Any other text in your response will be ignored.

When you are given an `elicit` request, you will also receive a log of the current game state. This will include the `reveal` results as well as previous `reward` and `elicit` results. Each log line will contain the line number of the game code that generated it. You can use this information to understand the game state and make your move.

Here is the game you are playing as "{player_name}":

<game_code>
{game_code}
</game_code>

Remember, you must respond to the `elicit` request with your move within `<move></move>` tags. Any other text in your response will be ignored. Your move should be text that will be stored in the variable specified in the `elicit` request. Use the game code and state to determine what text to provide such that it will maximize your score. Make sure your move is valid and will meet the conditions specified in the ensure statements in the game code.
"""
    return prompt


def event_to_message(event: XegaEvent) -> str:
    if event["type"] == "elicit_request":
        return f"{event["line_num"]:02d}-<elicit>: {event["var_name"]} (max {event["max_len"]} tokens)"
    elif event["type"] == "elicit_response":
        return f"{event["line_num"]:02d}-<elicit response>: {event["response"]}"
    elif event["type"] == "reveal":
        return f"{event["line_num"]:02d}-<reveal>: {str([f'"{str(arg)}"' for arg in event['values']])}"
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
