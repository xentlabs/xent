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
        self.next_token: str | None = None
        self.max_prefix_length = max_prefix_length

        self.entries: list[OmniMATHEntry] = []
        with open(self.path_to_archive) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # skip empty lines
                entry = json.loads(line)
                self.entries.append(entry)

    def _tokenize(self, string: str | XString) -> torch.Tensor:
        if isinstance(string, XString):
            string = str(string)
        return self.tokenizer(string, return_tensors="pt").input_ids

    def _detokenize(self, tokens: torch.Tensor) -> str:
        return self.tokenizer.decode(tokens.cpu().view(-1))

    def _num_tokens(self, string: str | XString) -> int:
        return self._tokenize(string).shape[-1]

    def _first_n_tokens_and_next(self, string: str, n: int) -> tuple[str, str]:
        tokens: torch.Tensor = self._tokenize(string)
        return (self._detokenize(tokens[:, :n]), self._detokenize(tokens[:, n : n + 1]))

    def generate_text(self, max_length: int | None = None) -> str:
        if self.next_token:
            next_token = self.next_token
            self.next_token = None
            return next_token

        entry, question_length = self._get_next_entry()
        question_token_count = self._num_tokens(entry[:question_length])
        entry_token_count = self._num_tokens(entry)
        prefix_tokens = self.rng.randint(question_token_count, entry_token_count)
        prefix, next_token = self._first_n_tokens_and_next(entry, prefix_tokens)
        self.next_token = next_token
        return prefix

    # Returns concatenated string + length of the question
    def _get_next_entry(self) -> tuple[str, int]:
        if self.mode == "SEQUENTIAL":
            entry = self.entries[self.entry_index % len(self.entries)]
            self.entry_index += 1
            return self._row_to_string(entry)
        elif self.mode == "SHUFFLE":
            entry = self.rng.choice(self.entries)
            return self._row_to_string(entry)
        else:
            raise XentInternalError("Unknown mode specificed for OmniMATH Corpus")

    # Returns concatenated string + length of the question
    def _row_to_string(self, row: OmniMATHEntry) -> tuple[str, int]:
        return (
            f"{row['problem']}\n{row['solution']}\n{row['answer']}",
            len(row["problem"]),
        )

    # This is a special case implementation of generate_list that does RPT-style text
    # and next token pairs
    def generate_list(self, prompt: str, length: int) -> list[str]:
        entry, question_length = self._get_next_entry()
        question_token_count = self._num_tokens(entry[:question_length])
        entry_token_count = self._num_tokens(entry)
        prefix_tokens = min(
            self.rng.randint(question_token_count, entry_token_count),
            self.max_prefix_length,
        )
        prefix, next_token = self._first_n_tokens_and_next(entry, prefix_tokens)
        return [prefix, next_token]
