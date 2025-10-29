import random
import re
import string
from collections.abc import Callable, Iterable
from typing import Any

from xent.common.configuration_types import ExecutableGameMap
from xent.common.constants import (
    ALL_PLAYERS,
    ALL_REGISTERS,
    LIST_REGISTERS,
    NUM_VARIABLES_PER_REGISTER,
    PUBLIC_REGISTERS,
    STATIC_REGISTERS,
)
from xent.common.token_xent_list import TokenXentList
from xent.common.x_flag import XFlag
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.runtime.judge import Judge
from xent.runtime.players.base_player import XGP
from xent.runtime.players.default_players import MockXGP


def build_locals(player: XGP, npcs: list[XGP], game_config: ExecutableGameMap):
    local_vars: dict[str, Any] = dict()

    for i in range(NUM_VARIABLES_PER_REGISTER):
        for t in ALL_REGISTERS:
            var_name = t if i == 0 else f"{t}{i}"
            if t in LIST_REGISTERS:
                local_vars[var_name] = XList(
                    [],
                    static=t in STATIC_REGISTERS,
                    public=t in PUBLIC_REGISTERS,
                    name=var_name,
                )
            else:
                local_vars[var_name] = XString(
                    "",
                    static=t in STATIC_REGISTERS,
                    public=t in PUBLIC_REGISTERS,
                    name=var_name,
                )

    local_vars[player.name] = player
    for npc in npcs:
        local_vars[npc.name] = npc

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
        only_uses_words=only_uses_words,
        sample=sample(judge.rng),
        shuffle=shuffle(judge.rng),
        punish_negative=punish_negative,
        reward_positive=reward_positive,
        xent=judge.xent,
        xed=judge.xed,
        nex=judge.nex,
        dex=judge.dex,
        is_true=judge.is_true,
        is_false=judge.is_false,
        first_n_tokens=judge.first_n_tokens,
        num_words=num_words,
        XString=XString,
        XList=XList,
    )

    flag_var_names = ["flag_1", "flag_2"]
    for flag_name in flag_var_names:
        globals[flag_name] = XFlag(flag_name, -1)

    return globals


remove_punctuation_translation = str.maketrans("", "", string.punctuation)


def sample(rng: random.Random) -> Callable[[XList], XString]:
    def sample_lambda(lst: XList) -> XString:
        if len(lst.items) == 0:
            return XString("")
        item = rng.choice(lst.items)
        return item

    return sample_lambda


def shuffle(rng: random.Random) -> Callable[[XList], XList]:
    def shuffle_lambda(lst: XList) -> XList:
        shuffled_items = list(lst)
        rng.shuffle(shuffled_items)
        return XList(
            shuffled_items,
            static=lst.static,
            public=lst.public,
            name=lst.name,
        )

    return shuffle_lambda


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


def remove_words(s: str | XString, words: Iterable[str | XString]) -> XString:
    # Define separators as whitespace or ASCII punctuation
    # This matches our tokenization (split on whitespace, ignore punctuation)
    separator_class = re.escape(string.punctuation) + r"\s"

    result = str(s)
    for word in words:
        escaped = re.escape(str(word))
        # We use a positive lookahead for the right separator: it allows it
        # to be the left separator of the next word and not be consumed.
        pattern = rf"(^|[{separator_class}]){escaped}(?=$|[{separator_class}])"
        # Remove the word, but keep the left separator. The right separator is
        # not part of the group.
        result = re.sub(pattern, r"\1", result, flags=re.IGNORECASE)

    result = re.sub(r"\s{2,}", " ", result).strip()
    return XString(result)


def remove_common_words(target: str | XString, other: str | XString | XList) -> XString:
    if isinstance(other, XList):
        common_words = other.items
    else:
        common_words = common_word_set(target, other)

    return remove_words(target, common_words)


def only_uses_chars(allowed_chars: str | XString, text: str | XString) -> bool:
    if isinstance(allowed_chars, XString):
        allowed_chars = str(allowed_chars)
    if isinstance(text, XString):
        text = str(text)

    allowed_set = set(allowed_chars)
    return all(char in allowed_set for char in text)


def only_uses_words(allowed_words: str | XString | XList, text: str | XString) -> bool:
    allowed_words_list: list[str] = []
    if isinstance(allowed_words, XString):
        allowed_words_list = str(allowed_words).split(" ")
    elif isinstance(allowed_words, str):
        allowed_words_list = allowed_words.split(" ")
    else:  # XList
        allowed_words_list = [str(i) for i in allowed_words.items]

    if isinstance(text, XString):
        text = str(text)
    text_words = text.split(" ")

    return all(word in allowed_words_list for word in text_words)


def punish_negative(reward: TokenXentList, scale: float = 64) -> float:
    score = reward.total_xent()
    if score >= 0:
        return score / scale

    return score * scale


def reward_positive(reward: TokenXentList, scale: float = 64) -> float:
    score = reward.total_xent()
    if score < 0:
        return score / scale

    return score * scale
