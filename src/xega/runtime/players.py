from xega.common.errors import XegaConfigurationError, XegaGameError
from xega.common.xega_types import PlayerName, XegaGameConfig
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


def make_player(player_name: PlayerName, game_config: XegaGameConfig) -> XGP:
    player_config = next(
        (x for x in game_config["players"] if x["name"] == player_name), None
    )
    if player_config is None:
        raise XegaGameError(
            f"Player configuration for {player_name} not found in game config."
        )
    player_type = player_config["player_type"]
    if player_type not in player_constructors:
        raise XegaConfigurationError(
            f"Player type {player_type} is not registered. Available types: {list(player_constructors.keys())}"
        )
    constructor = player_constructors[player_type]
    return constructor(
        player_name, player_config["id"], player_config.get("options", {}), game_config
    )
