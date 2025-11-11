import json
import random
from typing import Literal, TypedDict

from xent.common.errors import XentConfigurationError, XentInternalError
from xent.runtime.text_generation.text_generation import TextGenerator

CosmopediaGenerationMode = Literal["SEQUENTIAL", "SHUFFLE"]

"""
To convert from .parquet files to jsonl (which should be used here):

duckdb -c "COPY (SELECT * FROM read_parquet('path/to/file.parquet'))
           TO 'path/to/file.jsonl'
           (FORMAT JSON, ARRAY false);"
"""


class CosmopediaEntry(TypedDict):
    prompt: str
    text_token_length: int
    text: str
    seed_data: str
    format: str
    audience: str


class CosmopediaTextGenerator(TextGenerator):
    def __init__(
        self,
        path_to_archive: str,
        mode: CosmopediaGenerationMode,
        formats: list[str],
        seed: int | None,
    ):
        self.path_to_archive = path_to_archive
        self.mode = mode
        self.formats = formats
        self.entry_index = 0
        self.rng = random.Random(seed)
        with open(self.path_to_archive) as f:
            self.entries: list[CosmopediaEntry] = []
            all_entries = json.load(f)
            for entry in all_entries:
                if len(self.formats) == 0 or entry["format"] in self.formats:
                    self.entries.append(entry)

    def generate_text(self, max_length: int | None = None) -> str:
        entry = self._get_next_entry()
        if max_length is not None:
            return entry[:max_length]
        return entry

    def _get_next_entry(self) -> str:
        if self.mode == "SEQUENTIAL":
            entry = self.entries[self.entry_index % len(self.entries)]
            self.entry_index += 1
            return entry["text"]
        elif self.mode == "SHUFFLE":
            entry = self.rng.choice(self.entries)
            return entry["text"]
        else:
            raise XentInternalError("Unknown mode specificed for Cosmopedia Corpus")

    def generate_list(self, prompt: str, length: int) -> list[str]:
        raise XentConfigurationError(
            "CosmopediaTextGenerator doesn't support the generate_list interface"
        )
