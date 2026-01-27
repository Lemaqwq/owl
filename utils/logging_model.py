"""
Custom model backends with API logging for Gemini and OpenAI models.
"""

import json
import time
from typing import Any, Dict, List, Optional, Type, Union

from openai import Stream
from pydantic import BaseModel

from camel.messages import OpenAIMessage
from camel.models.anthropic_model import AnthropicModel
from camel.models.gemini_model import GeminiModel
from camel.models.openai_model import OpenAIModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter

from api.local_api_logger import log_completion, set_log_dir


def _get_model_name(model_type: Union[ModelType, str]) -> str:
    """Extract model name string from ModelType enum or string.

    ModelType inherits from str (via UnifiedModelType), so the enum member
    IS a string. However, str() and __str__() don't work due to MRO issues.

    Solution: Use format string f"{model_type}" which correctly extracts
    the string value because Python treats it as a string during formatting.
    """
    try:
        # Fallback: try string slicing (works for str subclasses)
        return model_type[:]

    except Exception:
        return "unknown_model"


class LoggingGeminiModel(GeminiModel):
    """
    Gemini model backend with API call logging.
    Inherits all behavior from GeminiModel and adds logging.
    """

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        """Request chat completion with API logging."""
        start_time = time.time()

        # Call parent method
        response = super()._request_chat_completion(messages, tools)

        duration_ms = (time.time() - start_time) * 1000

        # Log the API call (only for non-streaming responses)
        if not isinstance(response, Stream):
            self._log_response(messages, response, duration_ms)

        return response

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        """Request structured output with API logging."""
        start_time = time.time()

        # Call parent method
        response = super()._request_parse(messages, response_format, tools)

        duration_ms = (time.time() - start_time) * 1000

        # Log the API call
        self._log_response(messages, response, duration_ms)

        return response

    def _log_response(
        self,
        messages: List[OpenAIMessage],
        response: ChatCompletion,
        duration_ms: float,
    ):
        """Log API call using structured logger."""
        try:
            # Build request data
            request_data = {
                "model": _get_model_name(self.model_type),
                "messages": messages,
            }

            # Build response data with proper structure
            response_data = _build_response_data(response)

            log_completion(
                model=_get_model_name(self.model_type),
                request_data=request_data,
                response_data=response_data,
                duration_ms=duration_ms,
                api_key=self._api_key,
            )
        except Exception as e:
            print(f"Warning: Failed to log API call: {e}")


def _build_response_data(response: ChatCompletion) -> Dict[str, Any]:
    """Build response data dict from ChatCompletion object."""
    response_data = {}

    # Extract choices
    if response.choices and len(response.choices) > 0:
        choices = []
        for choice in response.choices:
            choice_data = {
                "message": {
                    "role": choice.message.role if choice.message else "assistant",
                    "content": choice.message.content if choice.message and choice.message.content else "",
                },
                "finish_reason": choice.finish_reason,
            }
            # Add tool_calls if present
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                tool_calls_list = []
                for tc in choice.message.tool_calls:
                    tc_dict = {
                        "id": getattr(tc, 'id', ''),
                        "type": getattr(tc, 'type', 'function'),
                    }
                    if hasattr(tc, 'function'):
                        tc_dict["function"] = {
                            "name": getattr(tc.function, 'name', ''),
                            "arguments": getattr(tc.function, 'arguments', '{}'),
                        }
                    tool_calls_list.append(tc_dict)
                choice_data["message"]["tool_calls"] = tool_calls_list
            choices.append(choice_data)
        response_data["choices"] = choices

    # Extract usage
    if response.usage:
        response_data["usage"] = {
            "prompt_tokens": response.usage.prompt_tokens or 0,
            "completion_tokens": response.usage.completion_tokens or 0,
            "total_tokens": response.usage.total_tokens or 0,
        }

    # Add model and id
    if hasattr(response, 'model'):
        response_data["model"] = response.model
    if hasattr(response, 'id'):
        response_data["id"] = response.id

    return response_data


def create_logging_gemini_model(
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> LoggingGeminiModel:
    """Factory function to create LoggingGeminiModel."""
    return LoggingGeminiModel(
        model_type=model_type,
        model_config_dict=model_config_dict,
        api_key=api_key,
        url=url,
        timeout=timeout,
    )


class LoggingOpenAIModel(OpenAIModel):
    """
    OpenAI model backend with API call logging.
    Inherits all behavior from OpenAIModel and adds logging.
    """

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        """Run inference with API logging."""
        start_time = time.time()

        # Call parent method
        response = super()._run(messages, response_format, tools)

        duration_ms = (time.time() - start_time) * 1000

        # Log the API call (only for non-streaming responses)
        if not isinstance(response, Stream):
            self._log_response(messages, response, duration_ms)

        return response

    def _log_response(
        self,
        messages: List[OpenAIMessage],
        response: ChatCompletion,
        duration_ms: float,
    ):
        """Log API call using structured logger."""
        try:
            request_data = {
                "model": _get_model_name(self.model_type),
                "messages": messages,
            }
            response_data = _build_response_data(response)

            log_completion(
                model=_get_model_name(self.model_type),
                request_data=request_data,
                response_data=response_data,
                duration_ms=duration_ms,
                api_key=self._api_key,
            )
        except Exception as e:
            print(f"Warning: Failed to log API call: {e}")


def create_logging_openai_model(
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    token_counter: Optional[BaseTokenCounter] = None,
    timeout: Optional[float] = None,
) -> LoggingOpenAIModel:
    """Factory function to create LoggingOpenAIModel."""
    return LoggingOpenAIModel(
        model_type=model_type,
        model_config_dict=model_config_dict,
        api_key=api_key,
        url=url,
        token_counter=token_counter,
        timeout=timeout,
    )


class LoggingAnthropicModel(AnthropicModel):
    """
    Anthropic model backend with API call logging.
    Inherits all behavior from AnthropicModel and adds logging.
    """

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        """Request chat completion with API logging."""
        start_time = time.time()

        # Call parent method
        response = super()._request_chat_completion(messages, tools)

        duration_ms = (time.time() - start_time) * 1000

        # Log the API call (only for non-streaming responses)
        if not isinstance(response, Stream):
            self._log_response(messages, response, duration_ms)

        return response

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        """Request structured output with API logging."""
        start_time = time.time()

        # Call parent method
        response = super()._request_parse(messages, response_format, tools)

        duration_ms = (time.time() - start_time) * 1000

        # Log the API call
        self._log_response(messages, response, duration_ms)

        return response

    def _log_response(
        self,
        messages: List[OpenAIMessage],
        response: ChatCompletion,
        duration_ms: float,
    ):
        """Log API call using structured logger."""
        try:
            request_data = {
                "model": _get_model_name(self.model_type),
                "messages": messages,
            }
            response_data = _build_response_data(response)

            log_completion(
                model=_get_model_name(self.model_type),
                request_data=request_data,
                response_data=response_data,
                duration_ms=duration_ms,
                api_key=self._api_key,
            )
        except Exception as e:
            print(f"Warning: Failed to log API call: {e}")


def create_logging_anthropic_model(
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    token_counter: Optional[BaseTokenCounter] = None,
    timeout: Optional[float] = None,
) -> LoggingAnthropicModel:
    """Factory function to create LoggingAnthropicModel."""
    return LoggingAnthropicModel(
        model_type=model_type,
        model_config_dict=model_config_dict,
        api_key=api_key,
        url=url,
        token_counter=token_counter,
        timeout=timeout,
    )


# Alias for backwards compatibility
create_logging_model = create_logging_gemini_model
