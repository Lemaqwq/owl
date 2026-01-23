# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import copy
import json
import os
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from camel.configs import ANTHROPIC_API_PARAMS, AnthropicConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models._utils import try_modify_message_with_format
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    AnthropicTokenCounter,
    BaseTokenCounter,
    api_keys_required,
    dependencies_required,
)

logger = get_logger(__name__)


class AnthropicModel(OpenAICompatibleModel):
    r"""Anthropic API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of CLAUDE_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into `openai.ChatCompletion.create()`.  If
            :obj:`None`, :obj:`AnthropicConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Anthropic service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Anthropic service.
            (default: :obj:`https://api.anthropic.com/v1/`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`AnthropicTokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
    """

    @api_keys_required(
        [
            ("api_key", "ANTHROPIC_API_KEY"),
        ]
    )
    @dependencies_required('anthropic')
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = AnthropicConfig().as_dict()
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        url = (
            url
            or os.environ.get("ANTHROPIC_API_BASE_URL")
            or "https://api.anthropic.com/v1/"
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = AnthropicTokenCounter(self.model_type)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration is valid for anthropic
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Anthropic API.
        """
        for param in self.model_config_dict:
            if param not in ANTHROPIC_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Anthropic model backend."
                )

    @staticmethod
    def _preprocess_messages(
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Preprocess messages for Anthropic API compatibility.

        Anthropic's API rejects empty content strings in messages. This method
        fixes assistant messages that have tool_calls but empty content by
        removing the content field entirely (Anthropic accepts this).

        Args:
            messages (List[OpenAIMessage]): The messages to preprocess.

        Returns:
            List[OpenAIMessage]: The preprocessed messages.
        """
        processed = []
        for msg in messages:
            msg = dict(msg)  # Make a copy
            # Fix assistant messages with tool_calls but empty content
            if (
                msg.get("role") == "assistant"
                and msg.get("tool_calls")
                and not msg.get("content")
            ):
                # Remove empty content field - Anthropic accepts this
                msg.pop("content", None)
            processed.append(msg)
        return processed

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        r"""Override to preprocess messages for Anthropic compatibility."""
        messages = self._preprocess_messages(messages)
        return super()._request_chat_completion(messages, tools)

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        r"""Override to preprocess messages for Anthropic compatibility."""
        messages = self._preprocess_messages(messages)
        return await super()._arequest_chat_completion(messages, tools)

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Override for Anthropic: use JSON mode + prompt injection instead
        of OpenAI's beta.chat.completions.parse which is not supported.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Type[BaseModel]): The Pydantic model class for
                the expected response format.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            ChatCompletion: The chat completion response.
        """
        request_config = copy.deepcopy(self.model_config_dict)
        # Remove stream since structured response doesn't support it
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        # Deep copy messages to avoid modifying the original
        messages = copy.deepcopy(messages)
        # Preprocess messages for Anthropic compatibility
        messages = self._preprocess_messages(messages)
        # Inject JSON schema into the last user message
        try_modify_message_with_format(messages[-1], response_format)

        # Use JSON mode instead of beta.parse
        request_config["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        # Validate response against Pydantic model
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content
            # Strip markdown code blocks if present (common with Claude)
            content = self._strip_markdown_code_blocks(content)
            try:
                parsed = json.loads(content)
                # Validate with Pydantic
                response_format.model_validate(parsed)
                # Update response content with clean JSON
                response.choices[0].message.content = content
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in response: {e}")
            except ValidationError as e:
                logger.warning(f"Response validation warning: {e}")

        return response

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Async version of _request_parse for Anthropic.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Type[BaseModel]): The Pydantic model class for
                the expected response format.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            ChatCompletion: The chat completion response.
        """
        request_config = copy.deepcopy(self.model_config_dict)
        # Remove stream since structured response doesn't support it
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        # Deep copy messages to avoid modifying the original
        messages = copy.deepcopy(messages)
        # Preprocess messages for Anthropic compatibility
        messages = self._preprocess_messages(messages)
        # Inject JSON schema into the last user message
        try_modify_message_with_format(messages[-1], response_format)

        # Use JSON mode instead of beta.parse
        request_config["response_format"] = {"type": "json_object"}

        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        # Validate response against Pydantic model
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content
            # Strip markdown code blocks if present (common with Claude)
            content = self._strip_markdown_code_blocks(content)
            try:
                parsed = json.loads(content)
                # Validate with Pydantic
                response_format.model_validate(parsed)
                # Update response content with clean JSON
                response.choices[0].message.content = content
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in response: {e}")
            except ValidationError as e:
                logger.warning(f"Response validation warning: {e}")

        return response

    @staticmethod
    def _strip_markdown_code_blocks(content: str) -> str:
        r"""Strip markdown code blocks from content if present.

        Claude models sometimes wrap JSON in markdown code blocks like:
        ```json
        {...}
        ```

        Args:
            content (str): The content to process.

        Returns:
            str: The content with markdown code blocks removed.
        """
        content = content.strip()
        # Check for ```json or ``` at the start
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            if lines:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
