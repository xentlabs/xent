from xent.common.configuration_types import PlayerName

NUM_VARIABLES_PER_REGISTER = 4

ALL_REGISTERS = ["a", "b", "c", "l", "s", "t", "x", "y", "p"]
LIST_REGISTERS = ["l"]
STATIC_REGISTERS = ["a", "b", "c"]
PUBLIC_REGISTERS = ["a", "b", "p"]

ALL_PLAYERS: list[PlayerName] = ["black", "white", "alice", "bob", "carol", "env"]
OMNICISCIENT_PLAYERS: list[PlayerName] = ["black", "white", "env"]
ZERO_SUM_PLAYER_PAIRS: list[tuple[PlayerName, PlayerName]] = [("black", "white")]
NO_REWARD_PLAYERS: list[PlayerName] = ["env"]

SIMPLE_GAME_CODE = """
assign(s=story())
reveal(s)
elicit(x, 10)
assign(x1=remove_common_words(x, s)) # Remove any words in story from input text
reward(xed(s | x1))
""".strip()
