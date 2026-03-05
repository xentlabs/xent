import random

import torch

from xent.runtime.text_generation.text_generation import TextGenerator


class LengthConstrainedTextSampler:
    def __init__(self, text_generator: TextGenerator, rng: random.Random):
        self.text_generator = text_generator
        self.rng = rng

    def _is_single_token_round_trip(self, token_id_tensor: torch.Tensor) -> bool:
        token_text = self.text_generator.detokenize(token_id_tensor)
        round_trip = self.text_generator.tokenize(token_text)
        if round_trip.shape[-1] != 1:
            return False
        return int(round_trip.item()) == int(token_id_tensor.item())

    def generate_text(
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

    # RLP-style [prefix, next_token] generation
    def generate_list_next_token(
        self,
        min_length: int,
        max_length: int | None = None,
        randomize_length: bool = False,
    ) -> list[str]:
        while True:
            entry, entry_min_length = self.text_generator.get_next_entry()
            tokens = self.text_generator.tokenize(entry)
            entry_token_count = int(tokens.shape[-1])

            lower = max(1, entry_min_length)
            lower = max(lower, min_length)

            upper = entry_token_count - 1
            if max_length is not None:
                upper = min(upper, max_length)

            if upper < lower:
                continue

            prefix_tokens = (
                self.rng.randint(lower, upper) if randomize_length else upper
            )
            prefix_token_ids = tokens[:, :prefix_tokens]
            next_token_id = tokens[:, prefix_tokens : prefix_tokens + 1]

            if not self._is_single_token_round_trip(next_token_id):
                continue

            prefix = self.text_generator.detokenize(prefix_token_ids)
            next_token = self.text_generator.detokenize(next_token_id)
            return [prefix, next_token]
