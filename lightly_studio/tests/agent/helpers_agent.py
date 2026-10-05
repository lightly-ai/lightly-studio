"""Helpers for the tests of the agent."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.chat_messages import AgentMessage, AgentToolCall, AgentToolCallFunction
from lightly_studio.agent.result_store import ResultStore
from lightly_studio.models.collection import CollectionTable
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
) -> AgentContext:
    """Create an agent context with a fresh result store."""
    return AgentContext(
        session=session,
        collection=collection,
        selected_sample_ids=list(selected_sample_ids),
        result_store=ResultStore(),
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


class ScriptedChatModel:
    """A ``ChatModel`` that answers with fixed replies, in order, and records its input."""

    def __init__(self, replies: Sequence[AgentMessage]) -> None:
        self._replies = list(replies)
        self.received_messages: list[list[AgentMessage]] = []
        self.received_tools: list[list[dict[str, Any]]] = []

    def complete(
        self, messages: Sequence[AgentMessage], tools: Sequence[dict[str, Any]]
    ) -> AgentMessage:
        self.received_messages.append(list(messages))
        self.received_tools.append(list(tools))
        return self._replies.pop(0)
