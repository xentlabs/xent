from xega.common.errors import XegaConfigurationError, XegaGameError
from xega.common.xega_types import PlayerName, XegaGameConfig
from xega.runtime.base_player import XGP
from xega.runtime.default_players import DefaultXGP, MockXGP
from xega.runtime.human_player import HumanXGP


def make_player(player_name: PlayerName, game_config: XegaGameConfig) -> XGP:
    player_config = next(
        (x for x in game_config["players"] if x["name"] == player_name), None
    )
    if player_config is None:
        raise XegaGameError(
            f"Player configuration for {player_name} not found in game config."
        )
    player_type = player_config["player_type"]
    if player_type == "mock":
        return MockXGP(player_name, player_config.get("options", {}), game_config)
    elif player_type == "default":
        return DefaultXGP(
            player_config["name"], player_config.get("options", {}), game_config
        )
    elif player_type == "human":
        return HumanXGP(
            player_config["name"], player_config.get("options", {}), game_config
        )
    else:
        raise XegaConfigurationError(f"Unknown player type: {player_type}")
