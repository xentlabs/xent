from xega.common.configuration_types import ExecutableGameMap
from xega.common.errors import XegaConfigurationError
from xega.runtime.base_player import XGP
from xega.runtime.default_players import DefaultXGP, MockXGP
from xega.runtime.human_player import HumanXGP

player_constructors = {
    "mock": MockXGP,
    "default": DefaultXGP,
    "human": HumanXGP,
}


def register_player_type(player_type: str, constructor: type[XGP]) -> None:
    if player_type in player_constructors:
        raise XegaConfigurationError(
            f"Player type {player_type} is already registered."
        )
    player_constructors[player_type] = constructor


def make_player(executable_game_map: ExecutableGameMap) -> XGP:
    player_config = executable_game_map["player"]
    player_type = player_config["player_type"]
    if player_type not in player_constructors:
        raise XegaConfigurationError(
            f"Player type {player_type} is not registered. Available types: {list(player_constructors.keys())}"
        )
    constructor = player_constructors[player_type]
    return constructor(
        player_config["name"],
        player_config["id"],
        player_config.get("options", {}),
        executable_game_map,
    )
