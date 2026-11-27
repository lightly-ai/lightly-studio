"""Sends streamed chat completion requests with tools to OpenRouter.

OpenRouter speaks the OpenAI chat completions protocol, so a thin ``httpx`` client is
enough and no SDK is needed. The agent loop depends only on the ``ChatModel`` protocol, so
a test can replace the network with a scripted model.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from typing import Any, Protocol

import httpx

from lightly_studio.agent import openrouter_stream
from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.openrouter_stream import ModelDelta, StreamAssembler

# The path of the chat completions endpoint, relative to the base URL of the client.
_CHAT_COMPLETIONS_PATH = "chat/completions"

# The longest error text from OpenRouter that an exception repeats.
_MAX_DETAIL_CHARS = 1000


class AgentLLMError(Exception):
    """Raised when the language model gives no usable answer."""


class ChatModel(Protocol):
    """A language model that answers a chat transcript, possibly with tool calls."""

    def stream(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> Iterator[ModelDelta | AgentMessage]:
        """Stream the next assistant message for the transcript.

        Args:
            messages: The transcript so far, with the system message first.
            tools: The tool definitions in the OpenAI ``tools`` format.

        Returns:
            An iterator over the pieces of text while the model writes them. The last item
            is the complete assistant message. It has text, tool calls, or both.
        """
        ...


class OpenRouterChatModel:
    """A ``ChatModel`` that calls one model on OpenRouter."""

    def __init__(
        self, client: httpx.Client, api_key: str, model: str, reasoning_effort: str | None = None
    ) -> None:
        """Send every request through ``client``.

        Args:
            client: The client to send with. Its ``base_url`` names the OpenRouter API. The
                caller owns it and closes it.
            api_key: The OpenRouter API key.
            model: The OpenRouter model ID, for example ``openai/gpt-6-luna``.
            reasoning_effort: How much the model reasons before it answers, for example
                ``medium``. ``None`` sends no reasoning setting, so the model default applies.
        """
        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            # OpenRouter shows these two headers as the name of the app in its dashboard.
            "HTTP-Referer": "https://github.com/lightly-ai/lightly-studio",
            "X-Title": "LightlyStudio",
        }

    def stream(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> Iterator[ModelDelta | AgentMessage]:
        """Stream the next assistant message for the transcript.

        Args:
            messages: The transcript so far, with the system message first.
            tools: The tool definitions in the OpenAI ``tools`` format.

        Returns:
            An iterator over the pieces of text, then the complete assistant message.

        Raises:
            AgentLLMError: If OpenRouter cannot be reached, rejects the request, reports an
                error in the stream, or streams a message that is not complete.
        """
        assembler = StreamAssembler()
        try:
            with self._client.stream(
                "POST",
                _CHAT_COMPLETIONS_PATH,
                json=self._payload(messages=messages, tools=tools),
                headers=self._headers,
            ) as response:
                _raise_for_status(response=response)
                for chunk in _iter_chunks(response=response):
                    yield from assembler.add_chunk(chunk=chunk)
        except httpx.HTTPError as exc:
            raise AgentLLMError(f"OpenRouter cannot be reached: {exc}") from exc
        try:
            message = assembler.message()
        except ValueError as exc:
            raise AgentLLMError(str(exc)) from exc
        yield message

    def _payload(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [message.model_dump(exclude_none=True) for message in messages],
            "stream": True,
        }
        # The OpenAI format rejects an empty tool list.
        if tools:
            payload["tools"] = list(tools)
        if self._reasoning_effort is not None:
            payload["reasoning"] = {"effort": self._reasoning_effort}
        return payload


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == httpx.codes.OK:
        return
    response.read()
    raise AgentLLMError(
        f"OpenRouter answered {response.status_code}: {response.text[:_MAX_DETAIL_CHARS]}"
    )


def _iter_chunks(response: httpx.Response) -> Iterator[dict[str, Any]]:
    """Parse the chunks of a streamed response."""
    for data in openrouter_stream.iter_event_data(lines=response.iter_lines()):
        try:
            chunk: dict[str, Any] = json.loads(data)
        except ValueError as exc:
            raise AgentLLMError(f"OpenRouter streamed a chunk that is not JSON: {data}") from exc
        # OpenRouter reports an error of the upstream provider inside the stream.
        if "error" in chunk:
            raise AgentLLMError(
                f"OpenRouter reported an error: {str(chunk['error'])[:_MAX_DETAIL_CHARS]}"
            )
        yield chunk
