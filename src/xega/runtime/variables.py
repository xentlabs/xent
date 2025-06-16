import re
import string
from typing import Any, Dict, List

from xega.common.constants import (
    ALL_PLAYERS,
    ALL_REGISTERS,
    PUBLIC_REGISTERS,
    STATIC_REGISTERS,
)
from xega.common.x_flag import XFlag
from xega.common.x_string import XString
from xega.common.xega_types import XegaGameConfig
from xega.runtime.base_player import XGP
from xega.runtime.default_players import MockXGP
from xega.runtime.judge import Judge


def build_locals(players: List[XGP], game_config: XegaGameConfig):
    local_vars: Dict[str, Any] = dict()

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
            player = MockXGP(player_name, {}, game_config)
            local_vars[player_name] = player

    return local_vars


def build_globals(model_utils: Judge, map_seed: str):
    # Small hack to ensure that we get a different story each time
    map_seed_counter = int(map_seed.rsplit("_", 1)[1])
    secret_increment = {
        "counter": map_seed_counter % len(stories),
        "increment": map_seed_counter // len(stories) + 1,
    }
    globals: Any = dict(
        __builtins__=dict(
            len=len,
        ),
        story=story(secret_increment),
        word_set=word_set,
        common_word_set=common_word_set,
        remove_common_words=remove_common_words,
        xent=model_utils.xent,
        xed=model_utils.xed,
        nex=model_utils.nex,
        dex=model_utils.dex,
        first_n_tokens=model_utils.first_n_tokens,
        secret_increment=secret_increment,
        num_words=num_words,
        XString=XString,
    )

    flag_var_names = ["flag_1", "flag_2"]
    for flag_name in flag_var_names:
        globals[flag_name] = XFlag(flag_name, -1)

    return globals


def story(secret_increment):
    def get_story():
        next_story = stories[secret_increment["counter"]]

        secret_increment["counter"] += secret_increment["increment"]
        if secret_increment["counter"] >= len(stories):
            secret_increment["counter"] = 0
            secret_increment["increment"] += 1

        # Dont let increment go higher than the number of stories
        if secret_increment["increment"] >= len(stories):
            secret_increment["increment"] = 1

        return XString(next_story)

    return get_story


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


def remove_common_words(s1: str | XString, s2: str | XString):
    common_words = common_word_set(s1, s2)
    for word in common_words:
        s1 = re.sub(word, "", str(s1), flags=re.IGNORECASE)
    result = re.sub(r"\s{2,}", " ", str(s1)).strip()
    return XString(result)


stories = [
    "At the book club, I ran into this girl, Neila, who claims to only read books backwards: starting from the bottom-right corner of the last page and reading all the words in reverse order until the beginning, finishing with the title. Doesn't it spoil the fun of the story? Apparently not, she told me. The suspense is just distributed somewhat differently (some books' beginnings are apparently all too predictable), and some books get better or worse if you read them in one direction or another. She started reading backwards at age seven. Her name was sort of a predisposition.",
    'Going to psychic school is quite exciting, though somewhat stressful. Out of the big four subjects (Love, Work, Health, and Money), the one that is widely considered the hardest is Money, but it happens to be my favorite. Our Money teacher is quite a character. At the beginning of the semester, he took a sheet of paper with our names on it, put it on his desk, wrote something next to each of the names, and then put it into an envelope, which he sealed. "I already know your grades for the course, though you will only receive them after the final exam."',
    "Hello, it is today a lovely day to use my skills in differential geometry and in the calculus of variation to estimate how much grass I will be able to eat. I aim to produce a lot of milk and to write a lot of theorems for my children, because that's what the beauty of life is about, dear physicists and cheese-makers. Have a great day!",
    "I was born in Geneva, and grew up on the shores of Lake Geneva, like my ancestors. I am not wondering much about what is the meaning of life, because I already found it a long time ago. Only shallow people care about nonsensical ontologies. Life is about eating grass, playing video games, and getting qualitative insights into the long-term behavior of solutions to partial differential equations",
    "Tomorrow will be a special day, as we will be the 19th of January 2038, the so-called Epochalypse. Some are worried about it, but I believe nothing will happen, really, except that we will shed nostalgia tears while looking at an epoch counter.",
    "I can recommend this park to any horse or donkey interested in meeting interesting fellows. Something I also love is to watch the stars and the planets at night (there are shooting stars sometimes!). I would just warn you that the admission process is quite bureaucratic. That said, once you are admitted, if you don't mind the humid climate, you will never look back: the landscape is gorgeous, the company stimulating, and the grass quality second to none.",
    "Our daughter is growing quite fast, these days... I calculated that if she keeps growing at that pace, she will exceed the diameter of the Milky Way galaxy in a few decades. If this happens, at some point, I will have to explain to her that the universe is not infinite, and that we will have to find a new home. In the meantime, I will keep teaching her to recognize the notes on the piano.",
    "To find inspiration in my job, I look at timelapses showing motion of clouds, the ballet of the stars, the coming and going of tides, the growth of fungi, the construction of ant colonies, the sleep of crocodiles. To project myself into the timescales needed to determine how to rule our people, I need to watch a timelapse every morning. Being a dictator is not an easy job, there is no degree in it.",
    "Mercury is regularly voted the least interesting planet in the solar system. I think that this year, the jury ought to put more weight on the three-to-two spin-orbit resonance, a truly underrated phenomenon. In the satellite category, Deimos and Phobos are usually voted the most boring satellites out there; unfortunately for them, I think they are bound to stay in the top two; hard to find them any redeeming qualities.",
    "What happens if a crocodile, a rhinoceros, and an elephant fight against three lions, a giraffe, a hippo, two wildebeests, and a cheetah? Thanks to our new free savannah simulator, such important questions can now be answered decisively in a matter of minutes. To download it, and also to try our new office politics simulator (now available via a premium subscription), please click on the link in the description.",
    "Living in an apartment facing the world's ugliest statue is not for everyone, of course; it unmistakably becomes the centerpiece of all discussions with visitors and friends. That being said, it grows on you. Waking up in the morning to its sight is a reminder that we live in a special place on this planet. Our biggest fear is not that it disappears (it is simply too massive to be removed), but that one day it loses its crown to an even more ambitious artist's creation.",
    "Luke had bought a small piece of forest during the pandemic. He had gone to a public auction where two parcels were on sale. Luke acquired his for twenty-five times the estimated price, but it was well worth it. Every Sunday, Luke would go to his forest. He knew all the trees, and befriended a family of deer whose territory overlapped with his. Every Sunday, Luke brought them apples to eat; unlike the male deer, he never had to fight to acquire his territory, and he often felt the luckiest mammal on Earth.",
    "Megan was only looking for a medium-difficulty relationship with Scott, Zach, and Adam, but she had accidentally jumped into an expert-level one. It was not the question of whether they knew about each other (they did), but about higher-order forms of knowledge: whether Scott knew that Zach knew that Adam was seeing Megan, and whether Adam knew about Zach knowing for Scott, and so on, and so forth. As she would often explain to her friends, there was a dramatic difference between studying bounded rationality games in grad school and experiencing their full-blown computational hardness in real life. ",
    "Tony and I were childhood friends. We met at the local zoo. Back in the day, there was a young female Komodo dragon. There was a special spot for kids to watch, once a month, the gruesome spectacle of a deer or a boar being desiccated by the beast. Apparently we didn't like this show as much as the other kids, but we would talk about Komodos. It was the time Tony told me about the parthenogenesis thing. At that moment it felt like the most interesting thing I had ever heard in my life. Tony is now very succesful. While some say he's gotten rich by sketchy means, I have always known that the reason he got there was that he is blessed with the knowledge of some of the most delicate facts about our world. ",
    "With my magical sleepberry device, I can type my thoughts in the night without opening an eye. Actually, I don't even need to really wake up, so I can type my dreams, forget about them and rediscover them later. Five hundred nights ago, I dreamed of an AI that could sing as badly as our neighbor. It was truly awful, but I am not sure I would have remembered that almost a year and a half later. Based on the statistics, it seems that most people dreamed that night about a stock market crash that never happened.",
    "Len believed he could help individuals achieve their full potential thanks to a couple of clever management techniques, which he had detailed in his latest book. Rationalize, focus on your strengths. 10x your most valuable output, cut the 90% of your work that doesn't matter, he would repeat at length. Len deeply admired the great Leonardo da Vinci, with whom he shared more than a name. But even a genius like him fell short of delivering his full potential. He could have created so much more value for the world, had he focused on painting more Mona Lisas, say, instead of designing wooden helicopters.",
]
