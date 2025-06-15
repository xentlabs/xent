import logging
import pprint
from typing import List, Optional

from xega.common.xega_types import PlayerName, PlayerOptions, XegaEvent, XegaGameConfig
from xega.runtime.base_player import XGP


class HumanXGP(XGP):
    def __init__(
        self,
        name: PlayerName,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        super().__init__(name, options, game_config)
        self.event_history: List[XegaEvent] = []

    def add_score(self, score: float | int) -> None:
        self.score += score

    def get_score(self) -> float | int:
        return self.score

    def reset_score(self) -> None:
        self.score = 0.0

    async def make_move(self, var_name: str) -> str:
        print(f"************************************************")
        print(f"The game name: {self.game_config['game']['name']}")
        print("Game code:")
        print("```")
        print(self.game_config["game"]["code"])
        print("```\n")
        print(f"You are playing as: {self.name}")
        print("The history of events in the game so far:")
        for event in self.event_history:
            print("------event------")
            pprint.pprint(event)
            if event["type"] == "reward":
                print(f"Score: {event['value'].total_xent()}")
            print("\n")
        print("-------End of event history-------\n")

        print(
            f"You are now asked to make a move which will be stored in the variable: {var_name}"
        )
        move = input("Enter your move: ")
        return move

    def post(self, event: XegaEvent) -> None:
        logging.info(f"Player received: {event}")
        self.event_history.append(event)
