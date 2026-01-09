import json
import random
from typing import Literal, TypedDict

from xent.common.errors import XentConfigurationError, XentInternalError
from xent.runtime.text_generation.text_generation import TextGenerator

OmniMATHGenerationMode = Literal["SEQUENTIAL", "SHUFFLE"]

"""
To convert from .parquet files to jsonl (which should be used here):

duckdb -c "COPY (SELECT * FROM read_parquet('path/to/file.parquet'))
           TO 'path/to/file.jsonl'
           (FORMAT JSON, ARRAY false);"
"""


class OmniMATHEntry(TypedDict):
    domain: str
    difficulty: float
    problem: str
    solution: str
    answer: str
    source: str


class OmniMATHTextGenerator(TextGenerator):
    def __init__(
        self,
        path_to_archive: str,
        mode: OmniMATHGenerationMode,
        formats: list[str],
        seed: int | None,
    ):
        self.path_to_archive = path_to_archive
        self.mode = mode
        self.formats = formats
        self.entry_index = 0
        self.rng = random.Random(seed)
        with open(self.path_to_archive) as f:
            self.entries: list[OmniMATHEntry] = []
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
            return self._row_to_string(entry)
        elif self.mode == "SHUFFLE":
            entry = self.rng.choice(self.entries)
            return self._row_to_string(entry)
        else:
            raise XentInternalError("Unknown mode specificed for OmniMATH Corpus")

    def _row_to_string(self, row: OmniMATHEntry) -> str:
        return f"{row['problem']}\n{row['solution']}\n{row['answer']}"

    def generate_list(self, prompt: str, length: int) -> list[str]:
        raise XentConfigurationError(
            "OmniMATHTextGenerator doesn't support the generate_list interface"
        )
