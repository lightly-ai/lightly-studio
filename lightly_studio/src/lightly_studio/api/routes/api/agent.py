"""API routes of the AI agent chat."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lightly_studio.agent import agent_loop
from lightly_studio.agent.agent_events import AgentEvent, AgentStreamLine, TurnErrorEvent
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.openrouter_client import AgentLLMError, ChatModel, OpenRouterChatModel
from lightly_studio.agent.result_store import default_result_store
from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.plugins.operator_registry import operator_registry

# How long one call of the language model may take. A model that calls tools can think for a
# while before it answers.
_LLM_TIMEOUT_SECONDS = 120.0

agent_router = APIRouter()


class NdjsonStreamingResponse(StreamingResponse):
    """A stream of JSON objects, one per line.

    The media type is a class attribute, so the OpenAPI schema shows it for the route.
    """

    media_type = "application/x-ndjson"


class AgentChatRequest(BaseModel):
    """Request of one agent turn."""

    messages: list[AgentMessage] = Field(
        min_length=1,
        description=(
            "The transcript of earlier turns as the server returned it, then the new user message."
        ),
    )
    selected_sample_ids: list[UUID] = Field(
        default_factory=list, description="The samples that the user selected in the GUI."
    )


def get_chat_model() -> Generator[ChatModel, None, None]:
    """Create the OpenRouter model of one request.

    Raises:
        HTTPException: 503 if no OpenRouter API key is set.
    """
    api_key = env.LIGHTLY_STUDIO_OPENROUTER_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            detail="The AI agent is off. Set LIGHTLY_STUDIO_OPENROUTER_API_KEY to switch it on.",
        )
    with httpx.Client(
        base_url=env.LIGHTLY_STUDIO_OPENROUTER_BASE_URL, timeout=_LLM_TIMEOUT_SECONDS
    ) as client:
        yield OpenRouterChatModel(
            client=client,
            api_key=api_key,
            model=env.LIGHTLY_STUDIO_AGENT_MODEL,
            reasoning_effort=env.LIGHTLY_STUDIO_AGENT_REASONING_EFFORT,
        )


@agent_router.post(
    "/collections/{collection_id}/agent/chat",
    response_class=NdjsonStreamingResponse,
    responses={
        200: {
            "model": AgentStreamLine,
            "description": "The events of the turn, one JSON object per line.",
        }
    },
)
def agent_chat(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
    chat_model: Annotated[ChatModel, Depends(get_chat_model)],
    request: AgentChatRequest,
) -> NdjsonStreamingResponse:
    """Answer a chat message. The agent can search, select and tag samples.

    The answer streams the events of the turn while the agent works. A failure of the
    language model after the stream started arrives as a ``turn_error`` event.

    Raises:
        HTTPException: 400 if the collection is not an image collection.
    """
    _require_image_collection(collection=collection)
    context = AgentContext(
        session=session,
        collection=collection,
        selected_sample_ids=request.selected_sample_ids,
        result_store=default_result_store,
        operator_registry=operator_registry,
    )
    events = agent_loop.stream_agent_turn(
        chat_model=chat_model, context=context, history=request.messages
    )
    return NdjsonStreamingResponse(_to_lines(events=events))


@agent_router.post(
    "/collections/{collection_id}/agent/greeting",
    response_class=NdjsonStreamingResponse,
    responses={
        200: {
            "model": AgentStreamLine,
            "description": "The events of the greeting turn, one JSON object per line.",
        }
    },
)
def agent_greeting(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
    chat_model: Annotated[ChatModel, Depends(get_chat_model)],
) -> NdjsonStreamingResponse:
    """Start a conversation: the agent writes a brief analysis of the collection.

    The greeting asks the user what to do next. The GUI keeps the greeting as the first
    message of the transcript.

    Raises:
        HTTPException: 400 if the collection is not an image collection.
    """
    _require_image_collection(collection=collection)
    context = AgentContext(
        session=session,
        collection=collection,
        selected_sample_ids=[],
        result_store=default_result_store,
        operator_registry=operator_registry,
    )
    events = agent_loop.stream_greeting_turn(chat_model=chat_model, context=context)
    return NdjsonStreamingResponse(_to_lines(events=events))


def _require_image_collection(collection: CollectionTable) -> None:
    if collection.sample_type != SampleType.IMAGE:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail="The AI agent supports only image collections.",
        )


def _to_lines(events: Iterator[AgentEvent]) -> Iterator[str]:
    """Write each event as one line of JSON. A model failure becomes the last event."""
    try:
        for event in events:
            yield event.model_dump_json() + "\n"
    except AgentLLMError as exc:
        yield TurnErrorEvent(detail=str(exc)).model_dump_json() + "\n"
