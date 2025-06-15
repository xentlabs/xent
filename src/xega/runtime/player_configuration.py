from typing import Literal, NotRequired, Optional, TypedDict, cast

import torch
from typeguard import check_type

from xega.common.errors import XegaConfigurationError
from xega.common.util import dumps
from xega.common.xega_types import PlayerOptions

KNOWN_PROVIDER = Literal[
    "openai", "anthropic", "gemini", "grok", "ollama", "huggingface"
]


class DefaultXGPOptions(TypedDict):
    model: str
    provider: KNOWN_PROVIDER


class DefaultHFXGPOptions(
    DefaultXGPOptions,
):
    device: NotRequired[Optional[str]]
    load_in_8bit: NotRequired[Optional[bool]]
    load_in_4bit: NotRequired[Optional[bool]]
    torch_dtype: NotRequired[Optional[torch.dtype]]
    trust_remote_code: NotRequired[Optional[bool]]
    max_length: NotRequired[Optional[int]]
    temperature: NotRequired[Optional[float]]
    top_p: NotRequired[Optional[float]]
    do_sample: NotRequired[Optional[bool]]


def check_default_xgp_options(
    options: Optional[PlayerOptions],
) -> DefaultXGPOptions:
    if options is None:
        raise XegaConfigurationError(
            "Player options for default player type cannot be None. Please provide valid options."
        )
    try:
        check_type(options, DefaultXGPOptions)
        return cast(DefaultXGPOptions, options)
    except TypeError:
        raise XegaConfigurationError(
            f"Invalid options for default player type. Expected a dictionary with 'model' and 'provider' keys. Got: {dumps(options)}"
        )


def check_default_hf_xgp_options(
    options: Optional[PlayerOptions],
) -> DefaultHFXGPOptions:
    if options is None:
        raise XegaConfigurationError(
            "Player options for default HF player type cannot be None. Please provide valid options."
        )
    try:
        check_type(options, DefaultHFXGPOptions)
        return cast(DefaultHFXGPOptions, options)
    except TypeError:
        raise XegaConfigurationError(f"Invalid options for default HF player type.")
