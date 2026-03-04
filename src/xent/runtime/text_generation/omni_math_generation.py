"""
We use a special approach for omni MATH. So be wary using this text generator if you
are expecting it to operate similarly to the other text generators.
"""

import json
import random
from typing import Any, Literal, TypedDict

import torch

from xent.common.errors import XentInternalError
from xent.common.x_string import XString
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
        path_to_archive: str,  # Should be a jsonl file
        mode: OmniMATHGenerationMode,
        seed: int | None,
        tokenizer: Any,
        max_prefix_length: int = 1024,
    ):
        self.path_to_archive = path_to_archive
        self.mode = mode
        self.entry_index = 0
        self.rng = random.Random(seed)
        self.tokenizer = tokenizer
        self.max_prefix_length = max_prefix_length

        self.entries: list[OmniMATHEntry] = []
        with open(self.path_to_archive) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # skip empty lines
                entry = json.loads(line)
                self.entries.append(entry)

    def tokenize(self, string: str | XString) -> torch.Tensor:
        if isinstance(string, XString):
            string = str(string)
        return self.tokenizer(string, return_tensors="pt").input_ids

    def detokenize(self, tokens: torch.Tensor) -> str:
        return self.tokenizer.decode(tokens.cpu().view(-1))

    # Returns concatenated string + minimum allowed prefix token count (the full question)
    def get_next_entry(self) -> tuple[str, int]:
        if self.mode == "SEQUENTIAL":
            row = self.entries[self.entry_index % len(self.entries)]
            self.entry_index += 1
        elif self.mode == "SHUFFLE":
            row = self.rng.choice(self.entries)
        else:
            raise XentInternalError("Unknown mode specificed for OmniMATH Corpus")

        entry, question_char_length = self.row_to_string(row)
        question_token_count = int(
            self.tokenize(entry[:question_char_length]).shape[-1]
        )
        return entry, question_token_count

    # Returns concatenated string + length of the question in characters.
    # The caller can convert this to token count using tokenize(...).
    def row_to_string(self, row: OmniMATHEntry) -> tuple[str, int]:
        return (
            f"{row['problem']}\n{row['solution']}\n{row['answer']}",
            len(row["problem"]),
        )
