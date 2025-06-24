from abc import ABC, abstractmethod
from typing import Final, Optional

from xega.common.xega_types import PlayerName, PlayerOptions, XegaEvent, XegaGameConfig

"""
Xega Game Player (XGP) base class

This class serves as the base for all player implementations in the Xega game.
If you want to create a new player, then you should do 3 things:
1. Implement a new class that inherits from this class. Use `DefaultXGP` in default_players.py as an example.
2. Add a value to the `PlayerType` literal in xega_types.py that corresponds to your new player type.
3. Modify the `make_player` function in players.py to handle your new player type.

Once you have done these steps, you can use your new player type in the game configuration by specifying
the PlayerType you have added.
"""


class XGP(ABC):
    def __init__(
        self,
        name: PlayerName,
        options: Optional[PlayerOptions],
        game_config: XegaGameConfig,
    ):
        self._score = 0.0
        self._name: Final[PlayerName] = name
        self._options: Final[Optional[PlayerOptions]] = options
        self._game_config: Final[XegaGameConfig] = game_config

    @property
    def score(self) -> float:
        return self._score

    @property
    def name(self) -> PlayerName:
        return self._name

    @property
    def options(self) -> Optional[PlayerOptions]:
        return self._options

    @property
    def game_config(self) -> XegaGameConfig:
        return self._game_config

    @score.setter
    def score(self, value: float) -> None:
        self._score = value

    @abstractmethod
    def add_score(self, score: float) -> None:
        pass

    @abstractmethod
    def get_score(self) -> float:
        pass

    @abstractmethod
    def reset_score(self) -> None:
        pass

    @abstractmethod
    async def make_move(self, var_name: str) -> str:
        pass

    @abstractmethod
    async def post(self, event: XegaEvent) -> None:
        pass
