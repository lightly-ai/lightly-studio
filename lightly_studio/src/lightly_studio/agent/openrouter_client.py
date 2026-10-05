"""Sends chat completion requests with tools to OpenRouter.

OpenRouter speaks the OpenAI chat completions protocol, so a thin ``httpx`` client is
enough and no SDK is needed. The agent loop depends only on the ``ChatModel`` protocol, so
a test can replace the network with a scripted model.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from lightly_studio.agent.chat_messages import AgentMessage

# The path of the chat completions endpoint, relative to the base URL of the client.
_CHAT_COMPLETIONS_PATH = "chat/completions"

# The longest error text from OpenRouter that an exception repeats.
_MAX_DETAIL_CHARS = 1000


class AgentLLMError(Exception):
    """Raised when the language model gives no usable answer."""


class ChatModel(Protocol):
    """A language model that answers a chat transcript, possibly with tool calls."""

    def complete(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> AgentMessage:
        """Get the next assistant message for the transcript.

        Args:
            messages: The transcript so far, with the system message first.
            tools: The tool definitions in the OpenAI ``tools`` format.

        Returns:
            The assistant message. It has text, tool calls, or both.
        """
        ...


class OpenRouterChatModel:
    """A ``ChatModel`` that calls one model on OpenRouter."""

    def __init__(self, client: httpx.Client, api_key: str, model: str) -> None:
        """Send every request through ``client``.

        Args:
            client: The client to send with. Its ``base_url`` names the OpenRouter API. The
                caller owns it and closes it.
            api_key: The OpenRouter API key.
            model: The OpenRouter model ID, for example ``anthropic/claude-haiku-4.5``.
        """
        self._client = client
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            # OpenRouter shows these two headers as the name of the app in its dashboard.
            "HTTP-Referer": "https://github.com/lightly-ai/lightly-studio",
            "X-Title": "LightlyStudio",
        }

    def complete(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> AgentMessage:
        """Get the next assistant message for the transcript.

        Args:
            messages: The transcript so far, with the system message first.
            tools: The tool definitions in the OpenAI ``tools`` format.

        Returns:
            The assistant message.

        Raises:
            AgentLLMError: If OpenRouter cannot be reached, rejects the request, or
                answers a body without an assistant message.
        """
        payload = {
            "model": self._model,
            "messages": [message.model_dump(exclude_none=True) for message in messages],
            "tools": list(tools),
        }
        try:
            response = self._client.post(
                _CHAT_COMPLETIONS_PATH, json=payload, headers=self._headers
            )
        except httpx.HTTPError as exc:
            raise AgentLLMError(f"OpenRouter cannot be reached: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise AgentLLMError(
                f"OpenRouter answered {response.status_code}: {response.text[:_MAX_DETAIL_CHARS]}"
            )
        return _read_assistant_message(response=response)


def _read_assistant_message(response: httpx.Response) -> AgentMessage:
    """Read the first choice of a chat completion body."""
    try:
        body = response.json()
    except ValueError as exc:
        raise AgentLLMError("OpenRouter answered a body that is not JSON.") from exc
    # OpenRouter can report an error of the upstream provider with status 200.
    if "error" in body:
        raise AgentLLMError(
            f"OpenRouter reported an error: {str(body['error'])[:_MAX_DETAIL_CHARS]}"
        )
    try:
        message: dict[str, Any] = body["choices"][0]["message"]
        return AgentMessage.model_validate(message)
    except (KeyError, IndexError, TypeError, ValidationError) as exc:
        raise AgentLLMError(
            f"OpenRouter answered an unexpected body: {str(body)[:_MAX_DETAIL_CHARS]}"
        ) from exc
