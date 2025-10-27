import hashlib
import logging
import math
import os
import random
from typing import Any, Self

import numpy as np
import torch
import torch.nn.functional as F
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)

from xent.common.token_xent_list import TokenXentList
from xent.common.x_string import XString
from xent.runtime.text_generation.judge_generation import JudgeGenerator
from xent.runtime.text_generation.text_generation import TextGenerator


class Judge:
    def __init__(
        self,
        model_name: str,
        hf_dir_path: str | None = None,
        text_generator: TextGenerator | None = None,
        max_generation_length: int = 50,
        model_params: dict[str, Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.hf_dir_path = hf_dir_path
        self.max_generation_length = max_generation_length
        self.device: torch.device = (
            torch.device("cuda")
            if torch.cuda.is_available()
            else (
                torch.device("mps") if torch.mps.is_available() else torch.device("cpu")
            )
        )
        model_kwargs: dict[str, Any] = dict(model_params or {})

        if (hf_dir_path is not None) and os.path.exists(hf_dir_path):
            model_path: str = os.path.join(hf_dir_path, model_name)
            self.tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(
                model_path
            )
            self.model: PreTrainedModel = AutoModelForCausalLM.from_pretrained(
                model_path, **model_kwargs
            )
            if "device_map" not in model_kwargs:
                self.model = self.model.to(self.device)  # type: ignore
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if "device_map" not in model_kwargs:
                model_kwargs["device_map"] = "auto"
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, **model_kwargs
            )
        self.rng = random.Random()

        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.max_generation_length: int | None = max_generation_length
        if max_generation_length <= 0:
            self.max_generation_length = None

        if text_generator is None:
            text_generator = JudgeGenerator(self.model, self.tokenizer)
        self.text_generator = text_generator
        self.model.eval()

    # TODO, we should encode the state of rng in here
    def serialize(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "hf_dir_path": self.hf_dir_path,
            "max_generation_length": self.max_generation_length,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        return cls(
            data["model_name"],
            data["hf_dir_path"],
            None,  # We don't serialize or deserialize text_generator
            data["max_generation_length"],
        )

    def tokenize(self, string: str | XString) -> torch.Tensor:
        if isinstance(string, XString):
            string = str(string)
        return self.tokenizer(string, return_tensors="pt").input_ids.to(
            self.model.device  # type: ignore[attr-defined]
        )

    def num_tokens(self, string: str | XString) -> int:
        return self.tokenize(string).shape[-1]

    def first_n_tokens(self, string: str | XString, n: int) -> str | XString:
        tokens: torch.Tensor = self.tokenize(string)
        if tokens.shape[-1] <= n:
            return string

        return XString(self.detokenize(tokens[:, :n]))

    def detokenize(self, tokens: torch.Tensor) -> str:
        return self.tokenizer.decode(tokens.cpu().view(-1))

    def comp_logits(self, tokens: torch.Tensor) -> torch.Tensor:
        with torch.inference_mode():
            result = self.model(tokens, return_dict=True)  # type: ignore[operator]
            return result.logits

    def xent(
        self,
        string: XString,
        preprompt: str = "",
    ) -> TokenXentList:
        raw_string: str = str(string)
        prefix: str = str(preprompt + string.prefix)

        tokenized_prefix: torch.Tensor = self.tokenize(prefix).to(torch.int64)
        tokenized_string: torch.Tensor = self.tokenize(raw_string).to(torch.int64)
        prefix_length: int = tokenized_prefix.shape[-1]
        tokens: torch.Tensor = torch.cat([tokenized_prefix, tokenized_string], dim=-1)
        logits: torch.Tensor = self.comp_logits(tokens).view(tokens.shape[-1], -1)
        tokens = tokens.view(-1)

        target_tokens: torch.Tensor = tokens[prefix_length + 1 :]

        xent_values: torch.Tensor = F.cross_entropy(
            logits[prefix_length:-1, :], target_tokens, reduction="none"
        )
        # Convert to bits
        xent_bits = xent_values / math.log(2)

        token_strings: list[str] = []
        for i in range(len(target_tokens)):
            single_token_tensor: torch.Tensor = target_tokens[i : i + 1].unsqueeze(0)
            token_str: str = self.detokenize(single_token_tensor)
            token_strings.append(token_str)

        paired_results: list[tuple[str, float]] = list(
            zip(token_strings, xent_bits.tolist(), strict=False)
        )
        txl: TokenXentList = TokenXentList(paired_results)
        logging.info(f"Xent for {string} with prefix {prefix}: {txl.total_xent()}")
        return txl

    def xed(self, string: XString, pre_prompt: str = "") -> TokenXentList:
        no_prefix: XString = XString(str(string))
        return self.xent(no_prefix, pre_prompt) - self.xent(string, pre_prompt)

    def nex(self, string: XString, pre_prompt: str = "") -> TokenXentList:
        result: TokenXentList = self.xent(string, pre_prompt)
        return result * -1

    def dex(self, string: XString, pre_prompt: str = "") -> TokenXentList:
        result: TokenXentList = self.xed(string, pre_prompt)
        return result * -1

    def generate_text(self) -> str:
        return self.text_generator.generate_text(self.max_generation_length)

    def generate_list(self, prompt: str, length: int) -> list[str]:
        return self.text_generator.generate_list(prompt, length)

    def is_true(self, condition: str) -> bool:
        evaluation_str = XString(f"""You are a core knowledge engine. Your function is to evaluate the factual accuracy of a given statement. When a statement is ambiguous, use the most reasonable human interpretation. Respond only with "true" or "false".

---
Statement: "2 plus 2 equals 4"
Evaluation: true
###
Statement: "2 plus 2 equals 5"
Evaluation: false
###
Statement: "The sky is blue"
Evaluation: true
###
Statement: "Pigs can fly"
Evaluation: false
###
Statement: "A triangle has three sides"
Evaluation: true
###
Statement: "{condition}"
Evaluation: """)
        true_score = self.xent(evaluation_str + "true").total_xent()
        false_score = self.xent(evaluation_str + "false").total_xent()
        return true_score < false_score

    def is_false(self, condition: str) -> bool:
        return not self.is_true(condition)

    def set_seed(self, global_seed: str, map_seed: str) -> None:
        seed = self.full_seed(global_seed, map_seed)
        int_seed = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        np.random.seed(int_seed)
        torch.manual_seed(int_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int_seed)
        self.rng = random.Random(seed)

    def full_seed(self, seed: str, map_seed: str) -> str:
        return f"{seed}_{map_seed}"
