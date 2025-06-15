from typing import List, Tuple

from xega.common.xega_types import PlayerName

ALL_REGISTERS = ["a", "b", "c", "s", "t", "x", "y", "p"]
STATIC_REGISTERS = ["a", "b", "c"]
PUBLIC_REGISTERS = ["a", "b", "p"]

ALL_PLAYERS: List[PlayerName] = ["black", "white", "alice", "bob", "carol", "env"]
OMNICISCIENT_PLAYERS: List[PlayerName] = ["black", "white", "env"]
ZERO_SUM_PLAYER_PAIRS: List[Tuple[PlayerName, PlayerName]] = [("black", "white")]
NO_REWARD_PLAYERS: List[PlayerName] = ["env"]
