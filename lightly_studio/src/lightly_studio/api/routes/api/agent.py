"""API routes of the AI agent chat."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lightly_studio.agent import agent_loop
from lightly_studio.agent.agent_loop import AgentTurnResult
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.openrouter_client import AgentLLMError, ChatModel, OpenRouterChatModel
from lightly_studio.agent.result_store import default_result_store
from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable, SampleType

# How long one call of the language model may take. A model that calls tools can think for a
# while before it answers.
_LLM_TIMEOUT_SECONDS = 120.0

agent_router = APIRouter()


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
            client=client, api_key=api_key, model=env.LIGHTLY_STUDIO_AGENT_MODEL
        )


@agent_router.post("/collections/{collection_id}/agent/chat", response_model=AgentTurnResult)
def agent_chat(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
    chat_model: Annotated[ChatModel, Depends(get_chat_model)],
    request: AgentChatRequest,
) -> AgentTurnResult:
    """Answer a chat message. The agent can search, select and tag samples.

    Raises:
        HTTPException: 400 if the collection is not an image collection, 502 if the
            language model gives no usable answer.
    """
    if collection.sample_type != SampleType.IMAGE:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail="The AI agent supports only image collections.",
        )
    context = AgentContext(
        session=session,
        collection=collection,
        selected_sample_ids=request.selected_sample_ids,
        result_store=default_result_store,
    )
    try:
        return agent_loop.run_agent_turn(
            chat_model=chat_model, context=context, history=request.messages
        )
    except AgentLLMError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_GATEWAY, detail=str(exc)) from exc
