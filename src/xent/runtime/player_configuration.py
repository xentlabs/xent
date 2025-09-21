from typing import Any, Literal, NotRequired, TypedDict, cast

import torch
from typeguard import check_type

from xent.common.configuration_types import PlayerOptions
from xent.common.errors import XentConfigurationError
from xent.common.util import dumps

KNOWN_PROVIDER = Literal[
    "openai",
    "anthropic",
    "gemini",
    "grok",
    "ollama",
    "huggingface",
    "deepseek",
    "moonshot",
]


class DefaultXGPOptions(TypedDict):
    model: str
    provider: KNOWN_PROVIDER
    request_params: NotRequired[dict[str, Any]]


class DefaultHFXGPOptions(
    DefaultXGPOptions,
):
    device: NotRequired[str | None]
    load_in_8bit: NotRequired[bool | None]
    load_in_4bit: NotRequired[bool | None]
    torch_dtype: NotRequired[torch.dtype | None]
    trust_remote_code: NotRequired[bool | None]
    max_length: NotRequired[int | None]
    temperature: NotRequired[float | None]
    top_p: NotRequired[float | None]
    do_sample: NotRequired[bool | None]


def check_default_xgp_options(
    options: PlayerOptions | None,
) -> DefaultXGPOptions:
    if options is None:
        raise XentConfigurationError(
            "Player options for default player type cannot be None. Please provide valid options."
        )
    try:
        check_type(options, DefaultXGPOptions)
        return cast(DefaultXGPOptions, options)
    except TypeError:
        raise XentConfigurationError(
            f"Invalid options for default player type. Expected a dictionary with 'model' and 'provider' keys. Got: {dumps(options)}"
        ) from None


def check_default_hf_xgp_options(
    options: PlayerOptions | None,
) -> DefaultHFXGPOptions:
    if options is None:
        raise XentConfigurationError(
            "Player options for default HF player type cannot be None. Please provide valid options."
        )
    try:
        check_type(options, DefaultHFXGPOptions)
        return cast(DefaultHFXGPOptions, options)
    except TypeError:
        raise XentConfigurationError(
            "Invalid options for default HF player type."
        ) from None
