from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Mapping
from typing import Final

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
)
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import XentEvent

"""
Xent Game Player (XGP) base class

This class serves as the base for all player implementations in the Xent game.
If you want to create a new player, then you should do 3 things:
1. Implement a new class that inherits from this class. Use `DefaultXGP` in default_players.py as an example.
2. Add a value to the `PlayerType` literal in xent_types.py that corresponds to your new player type.
3. Modify the `make_player` function in players.py to handle your new player type.

Once you have done these steps, you can use your new player type in the game configuration by specifying
the PlayerType you have added.
"""

MoveResult = namedtuple(
    "MoveResult", ["response", "token_usage", "prompts", "full_response"]
)


class XGP(ABC):
    def __init__(
        self,
        name: PlayerName,
        id: str,
        options: PlayerOptions | None,
        executable_game_map: ExecutableGameMap,
    ):
        self._score = 0.0
        self._name: Final[PlayerName] = name
        self._id: Final[str] = id
        self._options: Final[PlayerOptions | None] = options
        self._executable_game_map: Final[ExecutableGameMap] = executable_game_map

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
    def executable_game_map(self) -> ExecutableGameMap:
        return self._executable_game_map

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
        self, var_name: str, register_state: Mapping[str, XString | XList]
    ) -> MoveResult:
        pass

    @abstractmethod
    async def post(self, event: XentEvent) -> None:
        pass
