from __future__ import annotations

import json
from collections.abc import Generator, Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.openrouter_client import AgentLLMError, ChatModel
from lightly_studio.api.app import app
from lightly_studio.api.routes.api import agent
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
)
from lightly_studio.dataset import env
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import tag_resolver
from tests import helpers_resolvers
from tests.agent import helpers_agent

_USER_MESSAGE = {"role": "user", "content": "Tag the selection as picked"}


def test_agent_chat(db_session: Session, test_client: TestClient) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    _override_chat_model(
        helpers_agent.ScriptedChatModel(
            replies=[
                helpers_agent.tool_call_message(
                    calls=[("call_1", "tag_samples", {"source": "selection", "tag_name": "picked"})]
                ),
                AgentMessage(role="assistant", content="Done."),
            ]
        )
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={"messages": [_USER_MESSAGE], "selected_sample_ids": [str(ids["b.jpg"])]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["content-type"] == "application/x-ndjson"
    events = _read_events(text=response.text)
    tag = tag_resolver.get_by_name(
        session=db_session, tag_name="picked", collection_id=collection.collection_id
    )
    assert tag is not None
    assert [event["type"] for event in events] == [
        "message",
        "message",
        "content_delta",
        "message",
        "turn_done",
    ]
    messages = [event["message"] for event in events if event["type"] == "message"]
    assert [message["role"] for message in messages] == ["assistant", "tool", "assistant"]
    assert messages[-1]["content"] == "Done."
    assert events[-1]["ui_actions"] == [
        {"type": "select_tag", "tag_id": str(tag.tag_id), "tag_name": "picked"}
    ]


@pytest.mark.parametrize(
    "prompt",
    [
        "Give me a brief overview of this collection. Highlight what is worth exploring.",
        "Give me the dataset statistics",
    ],
)
def test_agent_chat__answers_overview_without_model(
    db_session: Session, test_client: TestClient, prompt: str
) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    chat_model = helpers_agent.ScriptedChatModel(replies=[])
    _override_chat_model(chat_model)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={
            "messages": [{"role": "user", "content": prompt}],
            "selected_sample_ids": [str(ids["a.jpg"])],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert chat_model.received_messages == []
    events = _read_events(text=response.text)
    assert [event["type"] for event in events] == ["message", "message", "message", "turn_done"]
    call = events[0]["message"]["tool_calls"][0]
    result = events[1]["message"]
    assert call["function"]["name"] == "get_collection_overview"
    assert result["tool_call_id"] == call["id"]
    overview = json.loads(result["content"])
    assert overview["sample_count"] == 2
    assert overview["selected_sample_count"] == 1
    assert events[2]["message"]["content"] == "The collection has 2 images."
    assert events[-1]["ui_actions"] == []


def test_agent_chat__writes_answer_after_suggestion_only_step(
    db_session: Session, test_client: TestClient
) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    steps = {"steps": [{"label": "Select samples", "prompt": "Select two samples."}]}
    chat_model = helpers_agent.ScriptedChatModel(
        replies=[
            helpers_agent.tool_call_message(calls=[("overview", "get_collection_overview", {})]),
            helpers_agent.tool_call_message(calls=[("suggestions", "suggest_next_steps", steps)]),
            AgentMessage(role="assistant", content="The collection has 2 samples."),
        ]
    )
    _override_chat_model(chat_model)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Give me the dataset statistics and compare them with my selection.",
                }
            ]
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    events = _read_events(text=response.text)
    assert [event["type"] for event in events[-3:]] == ["content_delta", "message", "turn_done"]
    assert events[-3]["text"] == "The collection has 2 samples."
    assert events[-2]["message"]["content"] == "The collection has 2 samples."
    assert len(chat_model.received_messages) == 3
    assert chat_model.received_tools[-1] == []
    overview = next(
        message
        for message in chat_model.received_messages[-1]
        if message.tool_call_id == "overview"
    )
    assert json.loads(overview.content or "")["sample_count"] == 2


def test_agent_chat__not_found(test_client: TestClient) -> None:
    _override_chat_model(helpers_agent.ScriptedChatModel(replies=[]))

    response = test_client.post(
        f"/api/collections/{uuid4()}/agent/chat", json={"messages": [_USER_MESSAGE]}
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_agent_chat__video_collection(db_session: Session, test_client: TestClient) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    _override_chat_model(helpers_agent.ScriptedChatModel(replies=[]))

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={"messages": [_USER_MESSAGE]},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_agent_chat__llm_error(db_session: Session, test_client: TestClient) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    _override_chat_model(_FailingChatModel(error=AgentLLMError("OpenRouter answered 401: bad key")))

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={"messages": [_USER_MESSAGE]},
    )

    # The stream has started when the model fails, so the error is the last event.
    assert response.status_code == HTTP_STATUS_OK
    assert _read_events(text=response.text) == [
        {"type": "turn_error", "detail": "OpenRouter answered 401: bad key"}
    ]


def test_agent_chat__no_api_key(
    db_session: Session, test_client: TestClient, mocker: MockerFixture
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    mocker.patch.object(env, "LIGHTLY_STUDIO_OPENROUTER_API_KEY", None)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={"messages": [_USER_MESSAGE]},
    )

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert "LIGHTLY_STUDIO_OPENROUTER_API_KEY" in response.json()["detail"]


def test_agent_chat__unexpected_error(db_session: Session, test_client: TestClient) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    _override_chat_model(_FailingChatModel(error=RuntimeError("database is locked")))

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/agent/chat",
        json={"messages": [_USER_MESSAGE]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert _read_events(text=response.text) == [
        {
            "type": "turn_error",
            "detail": "The agent stopped because of an internal error. See the server log.",
        }
    ]


@pytest.fixture(autouse=True)
def _clear_chat_model_override() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.pop(agent.get_chat_model, None)


class _FailingChatModel:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def stream(self, messages: Any, tools: Any) -> Iterator[AgentMessage]:
        del messages, tools
        raise self._error
        yield  # Makes this function a generator.


def _read_events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines()]


def _override_chat_model(chat_model: ChatModel) -> None:
    app.dependency_overrides[agent.get_chat_model] = lambda: chat_model
