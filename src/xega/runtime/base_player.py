from abc import ABC, abstractmethod
from typing import Final

from xega.common.x_string import XString
from xega.common.xega_types import (
    PlayerName,
    PlayerOptions,
    TokenUsage,
    XegaEvent,
    XegaGameConfig,
)

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
        id: str,
        options: PlayerOptions | None,
        game_config: XegaGameConfig,
    ):
        self._score = 0.0
        self._name: Final[PlayerName] = name
        self._id: Final[str] = id
        self._options: Final[PlayerOptions | None] = options
        self._game_config: Final[XegaGameConfig] = game_config

    @property
    def score(self) -> float:
        return self._score

    @score.setter
    def score(self, value: float) -> None:
        self._score = value

    @property
    def name(self) -> PlayerName:
        return self._name

    @property
    def id(self) -> str:
        return self._id

    @property
    def options(self) -> PlayerOptions | None:
        return self._options

    @property
    def game_config(self) -> XegaGameConfig:
        return self._game_config

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
    async def make_move(
        self, var_name: str, register_state: dict[str, XString]
    ) -> tuple[str, TokenUsage]:
        pass

    @abstractmethod
    async def post(self, event: XegaEvent) -> None:
        pass
