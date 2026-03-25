import random

import torch

from xent.runtime.text_generation.text_generation import TextGenerator

MASKED_PASSAGE_PLACEHOLDER = "[masked passage]"
MIN_MASKED_PASSAGE_DISTANCE = 10


class LengthConstrainedTextSampler:
    def __init__(self, text_generator: TextGenerator, rng: random.Random):
        self.text_generator = text_generator
        self.rng = rng

    def _has_same_tokens_round_trip(self, token_id_tensor: torch.Tensor) -> bool:
        token_text = self.text_generator.detokenize(token_id_tensor)
        round_trip = self.text_generator.tokenize(token_text)
        return torch.equal(round_trip.cpu(), token_id_tensor.cpu())

    def _sample_text_with_constraints(
        self,
        max_length: int | None,
        min_length: int,
        randomize_length: bool,
    ) -> str:
        while True:
            entry, entry_min_length = self.text_generator.get_next_entry()
            entry_tokens = self.text_generator.tokenize(entry)
            entry_token_count = int(entry_tokens.shape[-1])

            lower = max(0, entry_min_length)
            lower = max(lower, min_length)

            if max_length is None:
                upper = entry_token_count
            else:
                upper = min(max_length, entry_token_count)

            if upper < lower:
                continue

            chosen_length = (
                self.rng.randint(lower, upper) if randomize_length else upper
            )
            return self.text_generator.detokenize(entry_tokens[:, :chosen_length])

    def generate_text(
        self,
        max_length: int | None,
        min_length: int,
        randomize_length: bool,
    ) -> str:
        return self._sample_text_with_constraints(
            max_length=max_length,
            min_length=min_length,
            randomize_length=randomize_length,
        )

    def _choose_masked_starts(
        self, text_length: int, span_length: int, num_spans: int
    ) -> list[int]:
        starts: list[int] = []
        cursor = 0
        remaining_spans = num_spans

        for _ in range(num_spans):
            remaining_after = remaining_spans - 1
            min_suffix_length = remaining_after * (
                span_length + MIN_MASKED_PASSAGE_DISTANCE
            )
            max_start = text_length - span_length - min_suffix_length
            if max_start < cursor:
                raise ValueError(
                    "Sampled text is too short for the configured masked passage spacing"
                )
            start = self.rng.randint(cursor, max_start)
            starts.append(start)
            cursor = start + span_length + MIN_MASKED_PASSAGE_DISTANCE
            remaining_spans -= 1

        return starts

    def generate_masked(
        self,
        max_length: int | None,
        min_length: int,
        randomize_length: bool,
        num_masked_sequences: int,
    ) -> list[str]:
        original_text = self._sample_text_with_constraints(
            max_length=max_length,
            min_length=min_length,
            randomize_length=randomize_length,
        )
        span_length = max(1, len(original_text) // (2 * num_masked_sequences))
        masked_starts = self._choose_masked_starts(
            len(original_text), span_length, num_masked_sequences
        )

        masked_parts: list[str] = []
        cursor = 0
        for start in masked_starts:
            masked_parts.append(original_text[cursor:start])
            masked_parts.append(MASKED_PASSAGE_PLACEHOLDER)
            cursor = start + span_length
        masked_parts.append(original_text[cursor:])

        masked_text = "".join(masked_parts)
        return [original_text, masked_text]

    # RLP-style [prefix, next_token] generation
    def generate_list_next_token(
        self,
        min_length: int,
        max_length: int | None = None,
        randomize_length: bool = False,
        n: int = 1,
    ) -> list[str]:
        while True:
            entry, entry_min_length = self.text_generator.get_next_entry()
            tokens = self.text_generator.tokenize(entry)
            entry_token_count = int(tokens.shape[-1])

            lower = max(1, entry_min_length)
            lower = max(lower, min_length)

            upper = entry_token_count - n
            if max_length is not None:
                upper = min(upper, max_length)

            if upper < lower:
                continue

            prefix_tokens = (
                self.rng.randint(lower, upper) if randomize_length else upper
            )
            prefix_token_ids = tokens[:, :prefix_tokens]
            next_token_ids = tokens[:, prefix_tokens : prefix_tokens + n]

            if not self._has_same_tokens_round_trip(next_token_ids):
                continue

            prefix = self.text_generator.detokenize(prefix_token_ids)
            next_token = self.text_generator.detokenize(next_token_ids)
            return [prefix, next_token]
