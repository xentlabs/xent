from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Mapping
from typing import Any, Final, Self

from xent.common.configuration_types import (
    ExecutableGameMap,
    PlayerName,
    PlayerOptions,
    XentMetadata,
)
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import XentEvent

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
        self._metadata: Final[XentMetadata] = executable_game_map["metadata"]

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

    @property
    def metadata(self) -> XentMetadata:
        return self._metadata

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        pass

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
        self, var_name: str, register_states: Mapping[str, XString | XList]
    ) -> MoveResult:
        pass

    @abstractmethod
    async def post(self, event: XentEvent) -> None:
        pass
