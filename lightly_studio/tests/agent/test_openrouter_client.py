from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import httpx
import pytest

from lightly_studio.agent.chat_messages import AgentMessage, ContentDelta, ReasoningDelta
from lightly_studio.agent.openrouter_client import AgentLLMError, OpenRouterChatModel

_TOOLS = [{"type": "function", "function": {"name": "f", "parameters": {}}}]


class TestOpenRouterChatModel:
    def test_stream(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _sse_response(
                chunks=[
                    {"choices": [{"delta": {"reasoning": "Call f."}}]},
                    {"choices": [{"delta": {"content": "Calling."}}]},
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "f", "arguments": '{"x": 1}'},
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                ]
            )

        model = _create_model(handler=handler, reasoning_effort="medium")
        items = list(
            model.stream(messages=[AgentMessage(role="user", content="hello")], tools=_TOOLS)
        )

        assert items[:2] == [ReasoningDelta(text="Call f."), ContentDelta(text="Calling.")]
        reply = items[2]
        assert isinstance(reply, AgentMessage)
        assert reply.content == "Calling."
        assert reply.reasoning == "Call f."
        assert reply.tool_calls is not None
        assert reply.tool_calls[0].function.name == "f"
        assert reply.tool_calls[0].function.arguments == '{"x": 1}'
        assert len(items) == 3
        assert len(requests) == 1
        assert requests[0].url == "https://openrouter.test/api/v1/chat/completions"
        assert requests[0].headers["Authorization"] == "Bearer test-key"
        payload = json.loads(requests[0].content)
        assert payload == {
            "model": "test/model",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": _TOOLS,
            "stream": True,
            "reasoning": {"effort": "medium"},
        }

    def test_stream__no_reasoning_effort(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _sse_response(chunks=[{"choices": [{"delta": {"content": "Hi"}}]}])

        model = _create_model(handler=handler, reasoning_effort=None)
        list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))

        assert "reasoning" not in json.loads(requests[0].content)

    def test_stream__no_tools(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _sse_response(chunks=[{"choices": [{"delta": {"content": "Hi"}}]}])

        model = _create_model(handler=handler, reasoning_effort=None)
        list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))

        assert "tools" not in json.loads(requests[0].content)

    def test_stream__sends_reasoning_details_back(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _sse_response(chunks=[{"choices": [{"delta": {"content": "Ok"}}]}])

        details = [{"type": "reasoning.encrypted", "index": 0, "data": "c2VjcmV0"}]
        model = _create_model(handler=handler, reasoning_effort=None)
        list(
            model.stream(
                messages=[AgentMessage(role="assistant", content="A", reasoning_details=details)],
                tools=[],
            )
        )

        assert json.loads(requests[0].content)["messages"] == [
            {"role": "assistant", "content": "A", "reasoning_details": details}
        ]

    def test_stream__error_status(self) -> None:
        model = _create_model(
            handler=lambda _request: httpx.Response(status_code=401, text="bad key")
        )
        with pytest.raises(AgentLLMError, match="OpenRouter answered 401: bad key"):
            list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))

    def test_stream__error_in_stream(self) -> None:
        model = _create_model(
            handler=lambda _request: _sse_response(
                chunks=[
                    {"choices": [{"delta": {"content": "Hel"}}]},
                    {"error": {"message": "provider down"}, "choices": []},
                ]
            )
        )
        items = model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[])

        assert next(items) == ContentDelta(text="Hel")
        with pytest.raises(AgentLLMError, match="provider down"):
            next(items)

    def test_stream__chunk_not_json(self) -> None:
        model = _create_model(
            handler=lambda _request: httpx.Response(status_code=200, text="data: {oops\n\n")
        )
        with pytest.raises(AgentLLMError, match="not JSON"):
            list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))

    def test_stream__incomplete_tool_call(self) -> None:
        model = _create_model(
            handler=lambda _request: _sse_response(
                chunks=[
                    {"choices": [{"delta": {"tool_calls": [{"function": {"arguments": "{}"}}]}}]}
                ]
            )
        )
        with pytest.raises(AgentLLMError, match="without an ID or a name"):
            list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))

    def test_stream__network_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        model = _create_model(handler=handler)
        with pytest.raises(AgentLLMError, match="cannot be reached"):
            list(model.stream(messages=[AgentMessage(role="user", content="hi")], tools=[]))


def _sse_response(chunks: Sequence[dict[str, Any]]) -> httpx.Response:
    lines = [": OPENROUTER PROCESSING"]
    lines.extend(f"data: {json.dumps(chunk)}" for chunk in chunks)
    lines.append("data: [DONE]")
    return httpx.Response(status_code=200, text="\n\n".join(lines) + "\n\n")


def _create_model(handler: Any, reasoning_effort: str | None = None) -> OpenRouterChatModel:
    client = httpx.Client(
        base_url="https://openrouter.test/api/v1/", transport=httpx.MockTransport(handler)
    )
    return OpenRouterChatModel(
        client=client, api_key="test-key", model="test/model", reasoning_effort=reasoning_effort
    )
