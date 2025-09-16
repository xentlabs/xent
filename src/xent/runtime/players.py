from xent.common.configuration_types import ExecutableGameMap
from xent.common.errors import XentConfigurationError
from xent.runtime.base_player import XGP
from xent.runtime.default_players import DefaultXGP, MockXGP
from xent.runtime.human_player import HumanXGP
from xent.runtime.websocket_player import WebsocketXGP

player_constructors = {
    "mock": MockXGP,
    "default": DefaultXGP,
    "human": HumanXGP,
    "websocket": WebsocketXGP,
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
