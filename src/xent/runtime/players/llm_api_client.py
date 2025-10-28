import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

import google.genai as genai
import google.genai.errors as genai_errors
import google.genai.types as genai_types
import torch
from anthropic import APIError as AnthropicAPIError
from anthropic import AsyncAnthropic, NotGiven
from anthropic import AuthenticationError as AnthropicAuthenticationError
from anthropic import BadRequestError as AnthropicBadRequestError
from anthropic import InternalServerError as AnthropicInternalServerError
from anthropic import RateLimitError as AnthropicRateLimitError
from anthropic.types import MessageParam
from ollama import AsyncClient
from ollama import ResponseError as OllamaResponseError
from openai import APIError as OpenAIAPIError
from openai import AsyncOpenAI
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import BadRequestError as OpenAIBadRequestError
from openai import InternalServerError as OpenAIInternalServerError
from openai import RateLimitError as OpenAIRateLimitError
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from xent.common.configuration_types import PlayerOptions
from xent.common.errors import (
    XentApiError,
    XentAuthenticationError,
    XentConfigurationError,
    XentGameError,
    XentInternalServerError,
    XentInvalidRequestError,
    XentRateLimitError,
)
from xent.common.xent_event import LLMMessage, TokenUsage
from xent.runtime.players.player_configuration import (
    DefaultHFXGPOptions,
    check_default_hf_xgp_options,
    check_default_xgp_options,
)


def guess_provider_from_model(model: str) -> str:
    """
    Guess the provider based on the model name.
    This is a heuristic and may not be accurate for all models.
    """
    if "gpt" in model.lower() or "o3" in model.lower() or "o4" in model.lower():
        return "openai"
    elif "claude" in model.lower():
        return "anthropic"
    elif "gemini" in model.lower():
        return "gemini"
    elif "grok" in model.lower():
        return "grok"
    elif "deepseek" in model.lower():
        return "deepseek"
    elif "moonshot" in model.lower() or "kimi" in model.lower():
        return "moonshot"
    elif "/" in model and not model.startswith("ollama/"):
        return "huggingface"
    if ":" in model.lower() or model.lower().startswith("ollama/"):
        return "ollama"
    else:
        return "huggingface"


class LLMClient(ABC):
    def __init__(self, model: str):
        self._model = model
        self._input_token_count = 0
        self._output_token_count = 0

    @property
    def model(self) -> str:
        return self._model

    @property
    def input_token_count(self) -> int:
        return self._input_token_count

    @property
    def output_token_count(self) -> int:
        return self._output_token_count

    def increment_token_counts(self, input_tokens: int, output_tokens: int) -> None:
        self._input_token_count += input_tokens
        self._output_token_count += output_tokens
        logging.info(
            f"Current token usage for current game. Input tokens: {input_tokens}, output tokens: {output_tokens}, total input tokens: {self._input_token_count}, total output tokens: {self._output_token_count}"
        )

    @abstractmethod
    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        """Send a request to the LLM and return the response and token usage."""
        pass


class OllamaClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        ollama_host = os.environ.get("OLLAMA_HOST")
        self.client = AsyncClient(ollama_host) if ollama_host else AsyncClient()
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        try:
            response = await self.client.chat(
                **self.request_params, model=self.model, messages=messages
            )
            response_message = response["message"]["content"]
            input_tokens = response.get("prompt_eval_count", 0)
            output_tokens = response.get("eval_count", 0)
            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            self.increment_token_counts(input_tokens, output_tokens)
            return response_message, token_usage
        except OllamaResponseError as e:
            if e.status_code == 429:
                raise XentRateLimitError(
                    str(e), provider="ollama", status_code=e.status_code
                ) from e
            elif e.status_code in [401, 403]:
                raise XentAuthenticationError(
                    str(e), provider="ollama", status_code=e.status_code
                ) from e
            elif e.status_code == 400:
                raise XentInvalidRequestError(
                    str(e), provider="ollama", status_code=e.status_code
                ) from e
            elif e.status_code >= 500:
                raise XentInternalServerError(
                    str(e), provider="ollama", status_code=e.status_code
                ) from e
            else:
                raise XentApiError(
                    str(e), provider="ollama", status_code=e.status_code
                ) from e
        except Exception as e:
            raise XentGameError(
                f"An unexpected error occurred with Ollama client: {e}"
            ) from e


class OpenAIClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise XentConfigurationError("OPENAI_API_KEY environment variable not set.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        """Send a request to the LLM and return the response."""
        openai_api_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.warning("Warning: Skipping empty message")
                continue

            if role == "system":
                openai_api_messages.append(
                    ChatCompletionSystemMessageParam(content=content, role="system")
                )
            elif role == "user":
                openai_api_messages.append(
                    ChatCompletionUserMessageParam(content=content, role="user")
                )
            elif role == "assistant":
                openai_api_messages.append(
                    ChatCompletionAssistantMessageParam(
                        content=content, role="assistant"
                    )
                )
            else:
                logging.warning(
                    f"Warning: Skipping invalid message format for OpenAI API: {msg}"
                )

        try:
            response = await self.client.chat.completions.create(
                **self.request_params,
                model=self.model,
                messages=openai_api_messages,
            )
            input_token_count = getattr(
                getattr(response, "usage", {}), "prompt_tokens", 0
            )
            output_token_count = getattr(
                getattr(response, "usage", {}), "completion_tokens", 0
            )
            self.increment_token_counts(input_token_count, output_token_count)
            response_message = response.choices[0].message.content
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )
            if response_message is None:
                raise XentApiError(
                    "The API returned an empty message.", provider="openai"
                )
            return response_message, token_usage
        except OpenAIRateLimitError as e:
            raise XentRateLimitError(
                str(e), provider="openai", status_code=e.status_code
            ) from e
        except OpenAIAuthenticationError as e:
            raise XentAuthenticationError(
                str(e), provider="openai", status_code=e.status_code
            ) from e
        except OpenAIBadRequestError as e:
            raise XentInvalidRequestError(
                str(e), provider="openai", status_code=e.status_code
            ) from e
        except OpenAIInternalServerError as e:
            raise XentInternalServerError(
                str(e), provider="openai", status_code=e.status_code
            ) from e
        except OpenAIAPIError as e:
            raise XentApiError(str(e), provider="openai", status_code=500) from e


class AnthropicClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise XentConfigurationError(
                "ANTHROPIC_API_KEY environment variable not set."
            )
        self.client = AsyncAnthropic(api_key=api_key)
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        system_message: str | NotGiven = NotGiven()
        if messages and messages[0].get("role") == "system":
            system_message = str(messages[0].get("content", ""))
            messages = messages[1:]

        anthropic_api_messages: list[MessageParam] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.info("Warning: Skipping empty message")
                continue

            if role == "user":
                anthropic_api_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                anthropic_api_messages.append({"role": "assistant", "content": content})
            else:
                logging.info(
                    f"Warning: Skipping invalid message format for Anthropic API: {msg}"
                )

        if not anthropic_api_messages:
            raise XentInvalidRequestError(
                "Cannot send a request with no user/assistant messages.",
                provider="anthropic",
            )

        try:
            message = await self.client.messages.create(
                **self.request_params,
                max_tokens=4096,
                messages=anthropic_api_messages,
                model=self.model,
                system=system_message,
            )
            input_token_count = message.usage.input_tokens
            output_token_count = message.usage.output_tokens
            self.increment_token_counts(input_token_count, output_token_count)
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )
            if (
                message.content
                and hasattr(message.content[0], "text")
                and message.content[0].text
            ):
                return message.content[0].text, token_usage
            else:
                raise XentApiError(
                    "The API returned an empty or blocked message.",
                    provider="anthropic",
                )
        except AnthropicRateLimitError as e:
            raise XentRateLimitError(
                str(e), provider="anthropic", status_code=e.status_code
            ) from e
        except AnthropicAuthenticationError as e:
            raise XentAuthenticationError(
                str(e), provider="anthropic", status_code=e.status_code
            ) from e
        except AnthropicBadRequestError as e:
            raise XentInvalidRequestError(
                str(e), provider="anthropic", status_code=e.status_code
            ) from e
        except AnthropicInternalServerError as e:
            raise XentInternalServerError(
                str(e), provider="anthropic", status_code=e.status_code
            ) from e
        except AnthropicAPIError as e:
            raise XentApiError(str(e), provider="anthropic", status_code=500) from e


class GeminiClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        google_api_key = os.getenv("GEMINI_API_KEY")
        if not google_api_key:
            raise XentConfigurationError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=google_api_key)
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        gemini_contents: list[Any] = []
        system_instruction_content: str | None = None
        processed_messages = list(messages)

        if processed_messages and processed_messages[0].get("role") == "system":
            content = processed_messages[0].get("content")
            if content:
                system_instruction_content = str(content)
            processed_messages = processed_messages[1:]

        for msg in processed_messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.warning(f"Warning: Skipping empty message for Gemini: {msg}")
                continue

            gemini_role: str | None = None
            if role == "user":
                gemini_role = "user"
            elif role == "assistant":
                gemini_role = "model"
            elif role == "system":
                logging.warning(
                    f"Warning: Ignoring subsequent system message for Gemini: {msg}"
                )
                continue
            else:
                logging.warning(
                    f"Warning: Skipping invalid message role for Gemini API: {role} in {msg}"
                )
                continue

            if gemini_role:
                gemini_contents.append(
                    {"role": gemini_role, "parts": [{"text": str(content)}]}
                )

        if not gemini_contents and not system_instruction_content:
            raise XentInvalidRequestError(
                "Cannot send a request with no user/assistant messages and no system instruction.",
                provider="gemini",
            )

        try:
            response = await self.client.aio.models.generate_content(
                **self.request_params,
                model=self.model,
                contents=gemini_contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction_content
                ),
            )

            input_token_count = 0
            output_token_count = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_token_count = response.usage_metadata.prompt_token_count or 0
                output_token_count = response.usage_metadata.candidates_token_count or 0
            else:
                logging.debug("Gemini response did not contain usage_metadata.")

            self.increment_token_counts(input_token_count, output_token_count)
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )

            if hasattr(response, "text") and response.text:
                return response.text, token_usage
            else:
                feedback = getattr(response, "prompt_feedback", "N/A")
                raise XentApiError(
                    f"Gemini response is empty or was blocked. Feedback: {feedback}",
                    provider="gemini",
                )

        except genai_errors.ClientError as e:
            # Map specific client errors based on status code
            if e.code == 429:
                raise XentRateLimitError(str(e), provider="gemini") from e
            elif e.code in (401, 403):
                raise XentAuthenticationError(str(e), provider="gemini") from e
            else:
                raise XentInvalidRequestError(str(e), provider="gemini") from e
        except genai_errors.ServerError as e:
            raise XentInternalServerError(str(e), provider="gemini") from e
        except Exception as e:
            raise XentApiError(
                f"An unexpected error occurred: {e}", provider="gemini"
            ) from e


class GrokClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            raise XentConfigurationError("GROK_API_KEY environment variable not set.")
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        openai_api_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.warning("Warning: Skipping empty message")
                continue

            if role == "system":
                openai_api_messages.append(
                    ChatCompletionSystemMessageParam(content=content, role="system")
                )
            elif role == "user":
                openai_api_messages.append(
                    ChatCompletionUserMessageParam(content=content, role="user")
                )
            elif role == "assistant":
                openai_api_messages.append(
                    ChatCompletionAssistantMessageParam(
                        content=content, role="assistant"
                    )
                )
            else:
                logging.warning(
                    f"Warning: Skipping invalid message format for Grok API: {msg}"
                )

        try:
            response = await self.client.chat.completions.create(
                **self.request_params,
                model=self.model,
                messages=openai_api_messages,
            )
            input_token_count = getattr(
                getattr(response, "usage", {}), "prompt_tokens", 0
            )
            output_token_count = getattr(
                getattr(response, "usage", {}), "completion_tokens", 0
            )
            self.increment_token_counts(input_token_count, output_token_count)
            response_message = response.choices[0].message.content
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )
            if response_message is None:
                raise XentApiError(
                    "The API returned an empty message.", provider="grok"
                )
            return response_message, token_usage
        except OpenAIRateLimitError as e:
            raise XentRateLimitError(
                str(e), provider="grok", status_code=e.status_code
            ) from e
        except OpenAIAuthenticationError as e:
            raise XentAuthenticationError(
                str(e), provider="grok", status_code=e.status_code
            ) from e
        except OpenAIBadRequestError as e:
            raise XentInvalidRequestError(
                str(e), provider="grok", status_code=e.status_code
            ) from e
        except OpenAIInternalServerError as e:
            raise XentInternalServerError(
                str(e), provider="grok", status_code=e.status_code
            ) from e
        except OpenAIAPIError as e:
            raise XentApiError(str(e), provider="grok") from e


class DeepSeekClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise XentConfigurationError(
                "DEEPSEEK_API_KEY environment variable not set."
            )
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        openai_api_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.warning("Warning: Skipping empty message")
                continue

            if role == "system":
                openai_api_messages.append(
                    ChatCompletionSystemMessageParam(content=content, role="system")
                )
            elif role == "user":
                openai_api_messages.append(
                    ChatCompletionUserMessageParam(content=content, role="user")
                )
            elif role == "assistant":
                openai_api_messages.append(
                    ChatCompletionAssistantMessageParam(
                        content=content, role="assistant"
                    )
                )
            else:
                logging.warning(
                    f"Warning: Skipping invalid message format for Deepseek API: {msg}"
                )

        try:
            response = await self.client.chat.completions.create(
                **self.request_params,
                model=self.model,
                messages=openai_api_messages,
            )
            input_token_count = getattr(
                getattr(response, "usage", {}), "prompt_tokens", 0
            )
            output_token_count = getattr(
                getattr(response, "usage", {}), "completion_tokens", 0
            )
            self.increment_token_counts(input_token_count, output_token_count)
            response_message = response.choices[0].message.content
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )
            if response_message is None:
                raise XentApiError(
                    "The API returned an empty message.", provider="deepseek"
                )
            return response_message, token_usage
        except OpenAIRateLimitError as e:
            raise XentRateLimitError(
                str(e), provider="deepseek", status_code=e.status_code
            ) from e
        except OpenAIAuthenticationError as e:
            raise XentAuthenticationError(
                str(e), provider="deepseek", status_code=e.status_code
            ) from e
        except OpenAIBadRequestError as e:
            raise XentInvalidRequestError(
                str(e), provider="deepseek", status_code=e.status_code
            ) from e
        except OpenAIInternalServerError as e:
            raise XentInternalServerError(
                str(e), provider="deepseek", status_code=e.status_code
            ) from e
        except OpenAIAPIError as e:
            raise XentApiError(str(e), provider="deepseek") from e


class MoonshotClient(LLMClient):
    def __init__(self, model: str, request_params: dict[str, Any]):
        super().__init__(model)
        api_key = os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            raise XentConfigurationError(
                "MOONSHOT_API_KEY environment variable not set."
            )
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.moonshot.ai/v1"
        )
        self.request_params = request_params

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        openai_api_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                logging.warning("Warning: Skipping empty message")
                continue

            if role == "system":
                openai_api_messages.append(
                    ChatCompletionSystemMessageParam(content=content, role="system")
                )
            elif role == "user":
                openai_api_messages.append(
                    ChatCompletionUserMessageParam(content=content, role="user")
                )
            elif role == "assistant":
                openai_api_messages.append(
                    ChatCompletionAssistantMessageParam(
                        content=content, role="assistant"
                    )
                )
            else:
                logging.warning(
                    f"Warning: Skipping invalid message format for Moonshot API: {msg}"
                )

        try:
            response = await self.client.chat.completions.create(
                **self.request_params,
                model=self.model,
                messages=openai_api_messages,
            )
            input_token_count = getattr(
                getattr(response, "usage", {}), "prompt_tokens", 0
            )
            output_token_count = getattr(
                getattr(response, "usage", {}), "completion_tokens", 0
            )
            self.increment_token_counts(input_token_count, output_token_count)
            response_message = response.choices[0].message.content
            token_usage = TokenUsage(
                input_tokens=input_token_count, output_tokens=output_token_count
            )
            if response_message is None:
                raise XentApiError(
                    "The API returned an empty message.", provider="moonshot"
                )
            return response_message, token_usage
        except OpenAIRateLimitError as e:
            raise XentRateLimitError(
                str(e), provider="moonshot", status_code=e.status_code
            ) from e
        except OpenAIAuthenticationError as e:
            raise XentAuthenticationError(
                str(e), provider="moonshot", status_code=e.status_code
            ) from e
        except OpenAIBadRequestError as e:
            raise XentInvalidRequestError(
                str(e), provider="moonshot", status_code=e.status_code
            ) from e
        except OpenAIInternalServerError as e:
            raise XentInternalServerError(
                str(e), provider="moonshot", status_code=e.status_code
            ) from e
        except OpenAIAPIError as e:
            raise XentApiError(str(e), provider="moonshot") from e


class HuggingFaceClient(LLMClient):
    def __init__(
        self,
        model_name_or_path: str,
        device: str | None = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        torch_dtype: torch.dtype | None = None,
        trust_remote_code: bool = False,
        max_length: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.95,
        do_sample: bool = True,
    ):
        super().__init__(model_name_or_path)
        try:
            if device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device

            self.max_length = max_length
            self.temperature = temperature
            self.top_p = top_p
            self.do_sample = do_sample

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name_or_path,
                trust_remote_code=trust_remote_code,
                padding_side="left",
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            if torch_dtype is None:
                torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

            model_kwargs = {
                "pretrained_model_name_or_path": model_name_or_path,
                "trust_remote_code": trust_remote_code,
                "torch_dtype": torch_dtype,
            }
            if load_in_8bit:
                model_kwargs["load_in_8bit"] = True
            elif load_in_4bit:
                model_kwargs["load_in_4bit"] = True
            elif self.device == "cuda":
                model_kwargs["device_map"] = "auto"

            self.model_instance = AutoModelForCausalLM.from_pretrained(**model_kwargs)

            if not (load_in_8bit or load_in_4bit) and self.device != "cuda":
                self.model_instance = self.model_instance.to(self.device)

            self.model_instance.eval()
            logging.info(f"Loaded model {model_name_or_path} on {self.device}")
        except Exception as e:
            raise XentConfigurationError(
                f"Failed to load Hugging Face model '{model_name_or_path}': {e}"
            ) from e

    @classmethod
    def from_options(cls, options: DefaultHFXGPOptions) -> "HuggingFaceClient":
        constructor_args: Any = options.copy()
        constructor_args["model_name_or_path"] = constructor_args.pop("model")
        constructor_args.pop("provider", None)
        constructor_args = {k: v for k, v in constructor_args.items() if v is not None}
        return cls(**constructor_args)

    def _format_messages_to_prompt(self, messages: list[LLMMessage]) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                filtered_messages = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in messages
                    if msg.get("content")
                ]
                return self.tokenizer.apply_chat_template(
                    filtered_messages, tokenize=False, add_generation_prompt=True
                )
            except Exception as e:
                logging.warning(
                    f"Chat template failed: {e}. Falling back to simple formatting."
                )

        formatted_parts = []
        for msg in messages:
            role, content = msg.get("role", ""), msg.get("content", "")
            if not content:
                continue
            if role == "system":
                formatted_parts.append(f"System: {content}")
            elif role == "user":
                formatted_parts.append(f"User: {content}")
            elif role == "assistant":
                formatted_parts.append(f"Assistant: {content}")
            else:
                formatted_parts.append(content)

        prompt = "\n\n".join(formatted_parts)
        if messages and messages[-1].get("role") == "user":
            prompt += "\n\nAssistant:"
        return prompt

    async def request(self, messages: list[LLMMessage]) -> tuple[str, TokenUsage]:
        try:
            prompt = self._format_messages_to_prompt(messages)
            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=self.max_length
            ).to(self.device)
            input_length = inputs["input_ids"].shape[1]

            loop = asyncio.get_event_loop()
            output_ids = await loop.run_in_executor(
                None, self._generate, inputs["input_ids"], inputs.get("attention_mask")
            )

            generated_ids = output_ids[0][input_length:]
            response = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

            output_length = len(generated_ids)
            self.increment_token_counts(input_length, output_length)
            token_usage = TokenUsage(
                input_tokens=input_length, output_tokens=output_length
            )
            return response.strip(), token_usage
        except Exception as e:
            raise XentGameError(f"Hugging Face model generation failed: {e}") from e

    def _generate(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        with torch.no_grad():
            generation_config = GenerationConfig(
                max_new_tokens=self.max_length - input_ids.shape[1],
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=self.do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            return self.model_instance.generate(
                input_ids,
                attention_mask=attention_mask,
                generation_config=generation_config,
            )

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=True))


def make_client(unchecked_options: PlayerOptions | None) -> LLMClient:
    options = check_default_xgp_options(unchecked_options)
    provider = options["provider"]
    request_params = options.get("request_params", {})
    if provider == "openai":
        return OpenAIClient(options["model"], request_params)
    elif provider == "anthropic":
        return AnthropicClient(options["model"], request_params)
    elif provider == "gemini":
        return GeminiClient(options["model"], request_params)
    elif provider == "grok":
        return GrokClient(options["model"], request_params)
    elif provider == "deepseek":
        return DeepSeekClient(options["model"], request_params)
    elif provider == "moonshot":
        return MoonshotClient(options["model"], request_params)
    elif provider == "ollama":
        return OllamaClient(options["model"], request_params)
    elif provider == "huggingface":
        return HuggingFaceClient.from_options(
            check_default_hf_xgp_options(unchecked_options)
        )
    else:
        raise XentConfigurationError(f"Unsupported provider: {provider}")
