from typing import Any

from xent.common.configuration_types import ExecutableGameMap
from xent.common.errors import XentConfigurationError
from xent.runtime.players.base_player import XGP
from xent.runtime.players.default_players import DefaultXGP, MockXGP
from xent.runtime.players.halting_player import HaltingXGP
from xent.runtime.players.human_player import HumanXGP
from xent.runtime.players.websocket_player import WebsocketXGP

player_constructors = {
    "mock": MockXGP,
    "default": DefaultXGP,
    "human": HumanXGP,
    "websocket": WebsocketXGP,
    "halting": HaltingXGP,
}


def register_player_type(player_type: str, constructor: type[XGP]) -> None:
    if player_type in player_constructors:
        raise XentConfigurationError(
            f"Player type {player_type} is already registered."
        )
    player_constructors[player_type] = constructor


def make_player(executable_game_map: ExecutableGameMap) -> XGP:
    player_config = executable_game_map["player"]
    player_type = player_config["player_type"]
    if player_type not in player_constructors:
        raise XentConfigurationError(
            f"Player type {player_type} is not registered. Available types: {list(player_constructors.keys())}"
        )
    constructor = player_constructors[player_type]
    return constructor(
        player_config["name"],
        player_config["id"],
        player_config.get("options", {}),
        executable_game_map,
    )


def make_npcs(executable_game_map: ExecutableGameMap) -> list[XGP]:
    npcs: list[XGP] = []
    for npc_config in executable_game_map["metadata"].get("npcs", []):
        npc_type = npc_config["player_type"]
        if npc_type not in player_constructors:
            raise XentConfigurationError(
                f"Player type {npc_type} is not registered. Available types: {list(player_constructors.keys())}"
            )
        constructor = player_constructors[npc_type]
        npc = constructor(
            npc_config["name"],
            npc_config["id"],
            npc_config.get("options", {}),
            executable_game_map,
        )
        npcs.append(npc)

    return npcs


def deserialize_player(data: dict[str, Any]) -> XGP:
    player_type = data["player_type"]
    constructor = player_constructors[player_type]
    return constructor.deserialize(data)
