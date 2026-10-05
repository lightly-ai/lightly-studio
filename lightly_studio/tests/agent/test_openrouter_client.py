from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.openrouter_client import AgentLLMError, OpenRouterChatModel

_TOOLS = [{"type": "function", "function": {"name": "f", "parameters": {}}}]


class TestOpenRouterChatModel:
    def test_complete(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                status_code=200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "f", "arguments": '{"x": 1}'},
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

        model = _create_model(handler=handler)
        reply = model.complete(messages=[AgentMessage(role="user", content="hello")], tools=_TOOLS)

        assert reply.tool_calls is not None
        assert reply.tool_calls[0].function.name == "f"
        assert reply.tool_calls[0].function.arguments == '{"x": 1}'
        assert len(requests) == 1
        assert requests[0].url == "https://openrouter.test/api/v1/chat/completions"
        assert requests[0].headers["Authorization"] == "Bearer test-key"
        payload = json.loads(requests[0].content)
        assert payload == {
            "model": "test/model",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": _TOOLS,
        }

    def test_complete__error_status(self) -> None:
        model = _create_model(
            handler=lambda _request: httpx.Response(status_code=401, text="bad key")
        )
        with pytest.raises(AgentLLMError, match="OpenRouter answered 401: bad key"):
            model.complete(messages=[AgentMessage(role="user", content="hi")], tools=[])

    def test_complete__error_in_body(self) -> None:
        model = _create_model(
            handler=lambda _request: httpx.Response(
                status_code=200, json={"error": {"message": "provider down"}}
            )
        )
        with pytest.raises(AgentLLMError, match="provider down"):
            model.complete(messages=[AgentMessage(role="user", content="hi")], tools=[])

    def test_complete__no_choices(self) -> None:
        model = _create_model(
            handler=lambda _request: httpx.Response(status_code=200, json={"choices": []})
        )
        with pytest.raises(AgentLLMError, match="unexpected body"):
            model.complete(messages=[AgentMessage(role="user", content="hi")], tools=[])

    def test_complete__network_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        model = _create_model(handler=handler)
        with pytest.raises(AgentLLMError, match="cannot be reached"):
            model.complete(messages=[AgentMessage(role="user", content="hi")], tools=[])


def _create_model(handler: Any) -> OpenRouterChatModel:
    client = httpx.Client(
        base_url="https://openrouter.test/api/v1/", transport=httpx.MockTransport(handler)
    )
    return OpenRouterChatModel(client=client, api_key="test-key", model="test/model")
