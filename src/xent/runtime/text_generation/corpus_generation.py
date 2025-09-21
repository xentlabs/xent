import json
import random
from enum import Enum
from typing import TypedDict

from xent.common.errors import XentInternalError
from xent.runtime.text_generation.text_generation import TextGenerator


class CommunityArchiveMode(Enum):
    SEQUENTIAL = 1
    SHUFFLE = 2


class CommunityArchiveTweet(TypedDict):
    id: str
    full_text: str
    lang: str


class CommunityArchiveArchive(TypedDict):
    tweets: list[CommunityArchiveTweet]


class CommunityArchiveTextGenerator(TextGenerator):
    def __init__(
        self, path_to_archive: str, mode: CommunityArchiveMode, seed: int | None
    ):
        self.path_to_archive = path_to_archive
        self.mode = mode
        self.tweet_index = 0
        self.rng = random.Random(seed)
        with open(self.path_to_archive) as f:
            self.archive = json.load(f)

    def generate_text(self, max_length: int | None = None) -> str:
        tweet = self._get_next_tweet()
        if max_length is not None:
            return tweet[:max_length]
        return tweet

    def _get_next_tweet(self) -> str:
        if self.mode == CommunityArchiveMode.SEQUENTIAL:
            tweet = self.archive["tweets"][
                self.tweet_index % len(self.archive["tweets"])
            ]
            self.tweet_index += 1
            return tweet["full_text"]
        elif self.mode == CommunityArchiveMode.SHUFFLE:
            tweet = self.rng.choice(self.archive["tweets"])
            return tweet["full_text"]
        else:
            raise XentInternalError(
                "Unknown mode specificed for Community Archive Corpus"
            )
