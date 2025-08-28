import re
import string
from typing import Any

from xega.common.configuration_types import XegaGameConfig
from xega.common.constants import (
    ALL_PLAYERS,
    ALL_REGISTERS,
    PUBLIC_REGISTERS,
    STATIC_REGISTERS,
)
from xega.common.x_flag import XFlag
from xega.common.x_string import XString
from xega.runtime.base_player import XGP
from xega.runtime.default_players import MockXGP
from xega.runtime.judge import Judge


def build_locals(players: list[XGP], game_config: XegaGameConfig):
    local_vars: dict[str, Any] = dict()

    for i in range(game_config["num_variables_per_register"]):
        for t in ALL_REGISTERS:
            var_name = t if i == 0 else f"{t}{i}"
            local_vars[var_name] = XString(
                "",
                static=t in STATIC_REGISTERS,
                public=t in PUBLIC_REGISTERS,
                name=var_name,
            )

    for player in players:
        local_vars[player.name] = player

    for player_name in ALL_PLAYERS:
        if player_name not in local_vars:
            player = MockXGP(player_name, f"mock_{player_name}_id", {}, game_config)
            local_vars[player_name] = player

    return local_vars


def build_globals(judge: Judge):
    globals: Any = dict(
        __builtins__=dict(
            len=len,
        ),
        word_set=word_set,
        common_word_set=common_word_set,
        remove_common_words=remove_common_words,
        only_uses_chars=only_uses_chars,
        xent=judge.xent,
        xed=judge.xed,
        nex=judge.nex,
        dex=judge.dex,
        is_true=judge.is_true,
        is_false=judge.is_false,
        first_n_tokens=judge.first_n_tokens,
        num_words=num_words,
        XString=XString,
    )

    flag_var_names = ["flag_1", "flag_2"]
    for flag_name in flag_var_names:
        globals[flag_name] = XFlag(flag_name, -1)

    return globals


remove_punctuation_translation = str.maketrans("", "", string.punctuation)


def remove_punctuation(string: str | XString):
    if isinstance(string, XString):
        string = str(string)
    return string.translate(remove_punctuation_translation)


def lowercase_words(string: str | XString):
    if isinstance(string, XString):
        string = str(string)
    return remove_punctuation(string).lower().split()


def word_set(string: str | XString):
    return set(lowercase_words(string))


def num_words(string: str | XString):
    return len(word_set(string))


def common_word_set(s1: str | XString, s2: str | XString):
    return word_set(s1).intersection(word_set(s2))


def remove_common_words(s1: str | XString, s2: str | XString) -> XString:
    common_words = common_word_set(s1, s2)

    # Define separators as whitespace or ASCII punctuation
    # This matches our tokenization (split on whitespace, ignore punctuation)
    separator_class = re.escape(string.punctuation) + r"\s"

    result = str(s1)
    for word in common_words:
        escaped = re.escape(word)
        # We use a positive lookahead for the right separator: it allows it
        # to be the left separator of the next word and not be consumed.
        pattern = rf"(^|[{separator_class}]){escaped}(?=$|[{separator_class}])"
        # Remove the word, but keep the left separator. The right separator is
        # not part of the group.
        result = re.sub(pattern, r"\1", result, flags=re.IGNORECASE)

    result = re.sub(r"\s{2,}", " ", result).strip()
    return XString(result)


def only_uses_chars(allowed_chars: str | XString, text: str | XString) -> bool:
    if isinstance(allowed_chars, XString):
        allowed_chars = str(allowed_chars)
    if isinstance(text, XString):
        text = str(text)

    allowed_set = set(allowed_chars)
    return all(char in allowed_set for char in text)
