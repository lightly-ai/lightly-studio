"""Helpers for the tests of the agent."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.agent.agent_events import AgentEvent, MessageEvent
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.chat_messages import (
    AgentMessage,
    AgentToolCall,
    AgentToolCallFunction,
    ContentDelta,
    ReasoningDelta,
)
from lightly_studio.agent.openrouter_stream import ModelDelta
from lightly_studio.agent.result_store import ResultStore
from lightly_studio.models.collection import CollectionTable
from lightly_studio.plugins.operator_registry import OperatorRegistry
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


def create_collection_with_embeddings(
    session: Session, embeddings_by_file: Mapping[str, list[float]]
) -> tuple[CollectionTable, dict[str, UUID]]:
    """Create an image collection whose default embedding model has the given vectors.

    Args:
        session: The database session.
        embeddings_by_file: The embedding of each image, by file name. All vectors must
            have the same length.

    Returns:
        The collection, and the sample ID of each image by file name.
    """
    collection = helpers_resolvers.create_collection(session=session)
    dimension = len(next(iter(embeddings_by_file.values())))
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=dimension,
        set_as_default=True,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=file_name), embedding)
            for file_name, embedding in embeddings_by_file.items()
        ],
    )
    return collection, {image.file_name: image.sample_id for image in images}


def create_context(
    session: Session,
    collection: CollectionTable,
    selected_sample_ids: Sequence[UUID] = (),
    operator_registry: OperatorRegistry | None = None,
) -> AgentContext:
    """Create an agent context with a fresh result store, and an empty operator registry."""
    return AgentContext(
        session=session,
        collection=collection,
        selected_sample_ids=list(selected_sample_ids),
        result_store=ResultStore(),
        operator_registry=operator_registry or OperatorRegistry(),
    )


def tool_call_message(calls: Sequence[tuple[str, str, Mapping[str, Any]]]) -> AgentMessage:
    """Create an assistant message that calls tools.

    Args:
        calls: The ID, the tool name and the arguments of each call.
    """
    return AgentMessage(
        role="assistant",
        tool_calls=[
            AgentToolCall(
                id=call_id,
                function=AgentToolCallFunction(name=name, arguments=json.dumps(arguments)),
            )
            for call_id, name, arguments in calls
        ],
    )


def messages_of(events: Sequence[AgentEvent]) -> list[AgentMessage]:
    """Get the messages of the message events, in order."""
    return [event.message for event in events if isinstance(event, MessageEvent)]


class ScriptedChatModel:
    """A ``ChatModel`` that streams fixed replies, in order, and records its input.

    A reply streams its reasoning and its content as one piece each, then the message.
    """

    def __init__(self, replies: Iterable[AgentMessage]) -> None:
        self._replies = iter(replies)
        self.received_messages: list[list[AgentMessage]] = []
        self.received_tools: list[list[dict[str, Any]]] = []

    def stream(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> Iterator[ModelDelta | AgentMessage]:
        self.received_messages.append(list(messages))
        self.received_tools.append(list(tools))
        reply = next(self._replies)
        if reply.reasoning:
            yield ReasoningDelta(text=reply.reasoning)
        if reply.content:
            yield ContentDelta(text=reply.content)
        yield reply
