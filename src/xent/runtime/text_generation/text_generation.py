import random
from abc import ABC, abstractmethod

import torch

from xent.common.errors import XentConfigurationError
from xent.common.x_string import XString


class TextGenerator(ABC):
    rng: random.Random

    @abstractmethod
    def get_next_entry(self) -> tuple[str, int]:
        """Return (entry_text, min_entry_length_in_tokens)."""

    def tokenize(self, string: str | XString) -> torch.Tensor:
        if not hasattr(self, "tokenizer"):
            raise XentConfigurationError(
                f"{self.__class__.__name__} does not expose a tokenizer for token-level generation"
            )
        if isinstance(string, XString):
            string = str(string)
        return self.tokenizer(string, return_tensors="pt").input_ids  # type: ignore[attr-defined]

    def detokenize(self, tokens: torch.Tensor) -> str:
        if not hasattr(self, "tokenizer"):
            raise XentConfigurationError(
                f"{self.__class__.__name__} does not expose a tokenizer for token-level generation"
            )
        return self.tokenizer.decode(tokens.cpu().view(-1))  # type: ignore[attr-defined]

    def generate_list(self, prompt: str, length: int) -> list[str]:
        raise XentConfigurationError(
            f"{self.__class__.__name__} doesn't support the generate_list interface"
        )

    def generate_list_next_token(self, max_length: int | None = None) -> list[str]:
        del max_length
        raise XentConfigurationError(
            f"{self.__class__.__name__} doesn't support the generate_list_next_token interface"
        )
