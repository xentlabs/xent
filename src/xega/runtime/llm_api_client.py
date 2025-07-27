import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Literal, TypedDict

import google.genai as genai
import google.genai.types as genai_types
import torch
from anthropic import AsyncAnthropic, NotGiven
from anthropic.types import MessageParam
from ollama import AsyncClient
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from xega.common.errors import XegaConfigurationError
from xega.common.xega_types import PlayerOptions, TokenUsage
from xega.runtime.player_configuration import (
    DefaultHFXGPOptions,
    check_default_hf_xgp_options,
    check_default_xgp_options,
)

LLMRole = Literal["user", "assistant", "system"]


class LLMMessage(TypedDict):
    role: LLMRole
    content: str


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
    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        """Send a request to the LLM and return the response."""
        pass


class OllamaClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        self.client = AsyncClient()

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        """Send a request to the LLM and return the response."""
        response = await self.client.chat(model=self.model, messages=messages)
        response_message = response["message"]["content"]
        token_usage = TokenUsage(
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
        )
        return response_message, token_usage


class OpenAIClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_api_messages,
        )
        input_token_count = getattr(getattr(response, "usage", {}), "prompt_tokens", 0)
        output_token_count = getattr(
            getattr(response, "usage", {}), "completion_tokens", 0
        )
        self.increment_token_counts(input_token_count, output_token_count)
        response_message = response.choices[0].message.content
        token_usage = TokenUsage(
            input_tokens=input_token_count, output_tokens=output_token_count
        )
        return response_message, token_usage


class AnthropicClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
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
            raise ValueError("No valid user/assistant messages to send.")

        message = await self.client.messages.create(
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
        if message.content and hasattr(message.content[0], "text"):
            return getattr(message.content[0], "text", ""), token_usage
        else:
            return None, token_usage


class GeminiClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        google_api_key = os.getenv("GEMINI_API_KEY")
        if not google_api_key:
            logging.error(
                "GOOGLE_API_KEY environment variable not set for GeminiClient."
            )
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=google_api_key)

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        """Send a request to the LLM and return the response."""
        gemini_contents = []
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
            logging.warning(
                "Gemini request has no user/assistant messages and no system instruction."
            )
            return None, TokenUsage(input_tokens=0, output_tokens=0)

        if (
            system_instruction_content
            and gemini_contents
            and gemini_contents[0]["role"] != "user"
        ):
            logging.warning(
                "Gemini API may require the first message in 'contents' to be 'user' "
                f"when 'system_instruction' is present. Current first message role: {gemini_contents[0]['role']}"
            )

        try:
            response = await self.client.aio.models.generate_content(
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
                logging.warning(
                    f"Gemini response is empty or was possibly blocked. Prompt feedback: {getattr(response, 'prompt_feedback', 'N/A')}"
                )
                return None, token_usage

        except Exception as e:
            logging.error(f"Error during Gemini API request: {e}")
            return None, TokenUsage(input_tokens=0, output_tokens=0)


class GrokClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(
            api_key=os.getenv("GROK_API_KEY"),
            base_url="https://api.x.ai/v1",
        )

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        """Send a request to the Grok LLM and return the response."""
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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_api_messages,
        )
        input_token_count = getattr(getattr(response, "usage", {}), "prompt_tokens", 0)
        output_token_count = getattr(
            getattr(response, "usage", {}), "completion_tokens", 0
        )
        self.increment_token_counts(input_token_count, output_token_count)
        response_message = response.choices[0].message.content
        token_usage = TokenUsage(
            input_tokens=input_token_count, output_tokens=output_token_count
        )
        return response_message, token_usage


class DeepSeekClient(LLMClient):
    def __init__(self, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        """Send a request to Deepseek LLM and return the response."""
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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_api_messages,
        )
        input_token_count = getattr(getattr(response, "usage", {}), "prompt_tokens", 0)
        output_token_count = getattr(
            getattr(response, "usage", {}), "completion_tokens", 0
        )
        self.increment_token_counts(input_token_count, output_token_count)
        response_message = response.choices[0].message.content
        token_usage = TokenUsage(
            input_tokens=input_token_count, output_tokens=output_token_count
        )
        return response_message, token_usage


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

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Store generation parameters
        self.max_length = max_length
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=trust_remote_code,
            padding_side="left",  # Important for batch generation
        )

        # Set padding token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Determine dtype
        if torch_dtype is None:
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        # Load model with appropriate configuration
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

        # Move to device if not using device_map
        if not (load_in_8bit or load_in_4bit) and self.device != "cuda":
            self.model_instance = self.model_instance.to(self.device)

        self.model_instance.eval()

        logging.info(f"Loaded model {model_name_or_path} on {self.device}")

    @classmethod
    def from_options(cls, options: DefaultHFXGPOptions) -> "HuggingFaceClient":
        """Create a HuggingFaceClient from configuration options."""
        constructor_args: Any = options.copy()
        constructor_args["model_name_or_path"] = constructor_args.pop("model")
        constructor_args.pop("provider", None)
        constructor_args = {k: v for k, v in constructor_args.items() if v is not None}
        return cls(**constructor_args)

    def _format_messages_to_prompt(self, messages: list[LLMMessage]) -> str:
        """
        Format messages into a prompt string.
        Uses chat template if available, otherwise falls back to simple formatting.
        """
        # Check if the tokenizer has a chat template
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                # Filter out empty messages
                filtered_messages = []
                for msg in messages:
                    if msg.get("content"):
                        filtered_messages.append(
                            {"role": msg["role"], "content": msg["content"]}
                        )

                # Apply chat template
                prompt = self.tokenizer.apply_chat_template(
                    filtered_messages, tokenize=False, add_generation_prompt=True
                )
                return prompt
            except Exception as e:
                logging.warning(
                    f"Chat template failed: {e}. Falling back to simple formatting."
                )

        # Fallback: Simple formatting
        formatted_parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

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

        # Join with double newlines and add prompt for assistant
        prompt = "\n\n".join(formatted_parts)
        if messages and messages[-1].get("role") == "user":
            prompt += "\n\nAssistant:"

        return prompt

    async def request(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, TokenUsage]:
        try:
            # Format messages into prompt
            prompt = self._format_messages_to_prompt(messages)

            # Tokenize input
            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=self.max_length
            ).to(self.device)

            input_length = inputs["input_ids"].shape[1]

            # Run generation in executor to avoid blocking
            loop = asyncio.get_event_loop()
            output_ids = await loop.run_in_executor(
                None, self._generate, inputs["input_ids"], inputs.get("attention_mask")
            )

            # Decode output
            generated_ids = output_ids[0][input_length:]  # Remove input tokens
            response = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

            # Count tokens
            output_length = len(generated_ids)
            self.increment_token_counts(input_length, output_length)

            return response.strip(), TokenUsage(
                input_tokens=input_length, output_tokens=output_length
            )

        except Exception as e:
            logging.error(f"Error during generation: {e}")
            return None, TokenUsage(input_tokens=0, output_tokens=0)

    def _generate(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        """
        Synchronous generation method to be run in executor.
        """
        with torch.no_grad():
            generation_config = GenerationConfig(
                max_new_tokens=self.max_length - input_ids.shape[1],
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=self.do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

            output_ids = self.model_instance.generate(
                input_ids,
                attention_mask=attention_mask,
                generation_config=generation_config,
            )

        return output_ids

    def count_tokens(self, text: str) -> int:
        """
        Utility method to count tokens in a text string.
        """
        return len(self.tokenizer.encode(text, add_special_tokens=True))


def make_client(unchecked_options: PlayerOptions | None) -> LLMClient:
    options = check_default_xgp_options(unchecked_options)
    provider = options["provider"]
    if provider == "openai":
        return OpenAIClient(options["model"])
    elif provider == "anthropic":
        return AnthropicClient(options["model"])
    elif provider == "gemini":
        return GeminiClient(options["model"])
    elif provider == "grok":
        return GrokClient(options["model"])
    elif provider == "deepseek":
        return DeepSeekClient(options["model"])
    elif provider == "ollama":
        return OllamaClient(options["model"])
    elif provider == "huggingface":
        return HuggingFaceClient.from_options(
            check_default_hf_xgp_options(unchecked_options)
        )
    else:
        logging.error(
            f"Unsupported provider: {provider}. Please use a supported provider."
        )
        raise XegaConfigurationError(f"Unsupported provider: {provider}")
