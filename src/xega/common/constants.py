from xega.common.xega_types import PlayerName

ALL_REGISTERS = ["a", "b", "c", "s", "t", "x", "y", "p"]
STATIC_REGISTERS = ["a", "b", "c"]
PUBLIC_REGISTERS = ["a", "b", "p"]

ALL_PLAYERS: list[PlayerName] = ["black", "white", "alice", "bob", "carol", "env"]
OMNICISCIENT_PLAYERS: list[PlayerName] = ["black", "white", "env"]
ZERO_SUM_PLAYER_PAIRS: list[tuple[PlayerName, PlayerName]] = [("black", "white")]
NO_REWARD_PLAYERS: list[PlayerName] = ["env"]
