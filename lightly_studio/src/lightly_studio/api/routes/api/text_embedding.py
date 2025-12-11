"""This module contains the API routes for managing text embedding."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
)
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
    TextEmbedQuery,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.resolvers import dataset_resolver

text_embedding_router = APIRouter()
# Define a type alias for the EmbeddingManager dependency
EmbeddingManagerDep = Annotated[
    EmbeddingManager,
    Depends(lambda: EmbeddingManagerProvider.get_embedding_manager()),
]

class TextEmbedding(BaseModel):
    """Text embedding input model."""
    embedding: list[float] | None = Field(None, description="Text embedding to search for")
    model_id: UUID

@text_embedding_router.get("/text_embedding/embed_text", response_model=TextEmbedding)
def embed_text(
    session: SessionDep,
    embedding_manager: EmbeddingManagerDep,
    query_text: str = Query(..., description="The text to embed."),
    embedding_model_id: Annotated[
        UUID | None,
        Query(..., description="The ID of the embedding model to use."),
    ] = None,
) -> TextEmbedding:
    """Retrieve embeddings for the input text."""
    # TODO(Jonas, 12/2025): Remove this hack after dataset_id is provided from frontend
    # This is a hack, since at the moment, no valid embedding_model_id is passed from the frontend.
    # so we fetch the root_dataset_id, which will be used inside embed_text to get the default model
    # for this dataset.
    root_dataset = dataset_resolver.get_root_dataset(session=session)
    dataset_id = root_dataset.dataset_id
    try:
        text_embeddings = embedding_manager.embed_text(
            dataset_id=dataset_id,
            text_query=TextEmbedQuery(text=query_text, embedding_model_id=embedding_model_id),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            detail=f"{exc}",
        ) from None

    return text_embeddings
