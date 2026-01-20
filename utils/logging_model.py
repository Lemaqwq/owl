"""
Custom model backend using OpenAIModel with API logging.
"""

import time
from typing import Any, Dict, List, Optional, Type, Union

from openai import Stream
from pydantic import BaseModel

from camel.messages import OpenAIMessage
from camel.models.openai_model import OpenAIModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType

from api.llm_api_utils import log_api_call_simple


class LoggingOpenAIModel(OpenAIModel):
    """
    OpenAI model backend with API call logging.
    Inherits all behavior from OpenAIModel and adds logging.
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
        """Log API call using simple logger."""
        try:
            # Extract response content and tool calls
            content = ""
            tool_calls = None
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                content = message.content if message.content else ""
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    tool_calls = message.tool_calls

            # Extract token usage
            prompt_tokens = 0
            completion_tokens = 0
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0

            log_api_call_simple(
                model_name=str(self.model_type),
                messages=messages,
                response_content=content,
                tool_calls=tool_calls,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        except Exception as e:
            print(f"Warning: Failed to log API call: {e}")


def create_logging_model(
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> LoggingOpenAIModel:
    """Factory function to create LoggingOpenAIModel."""
    return LoggingOpenAIModel(
        model_type=model_type,
        model_config_dict=model_config_dict,
        api_key=api_key,
        url=url,
        timeout=timeout,
    )
