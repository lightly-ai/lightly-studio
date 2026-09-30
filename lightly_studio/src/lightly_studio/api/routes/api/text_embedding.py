"""This module contains the API routes for managing text embedding."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.embed import embed_samples
from lightly_studio.embed.errors import QueryEmbedderError
from lightly_studio.models.range import FloatRange
from lightly_studio.resolvers import similarity_range_resolver

text_embedding_router = APIRouter()


class SimilarityRangeRequest(BaseModel):
    """Request body for the similarity range of a text embedding."""

    text_embedding: list[float]


@text_embedding_router.get(
    "/text_embedding/for_collection/{collection_id}", response_model=list[float]
)
def embed_text(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="The ID of the collection for which to embed.")],
    query_text: str = Query(..., description="The text to embed."),
    embedding_model_id: Annotated[
        UUID | None,
        Query(..., description="The ID of the embedding model to use."),
    ] = None,
) -> list[float]:
    """Retrieve embeddings for the input text."""
    if embedding_model_id is not None:
        raise NotImplementedError(
            "Per-request embedding model override is not supported yet. Collection's "
            "default embedding model is always used."
        )
    try:
        text_embeddings = embed_samples.embed_text_for_collection(
            session=session, collection_id=collection_id, text=query_text
        )
    # The app exception handlers map these
    except QueryEmbedderError:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            detail=f"{exc}",
        ) from None

    return text_embeddings


@text_embedding_router.post("/collections/{collection_id}/similarity_range")
def get_similarity_range(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="The ID of the collection.")],
    body: SimilarityRangeRequest,
) -> FloatRange | None:
    """Get the min and max similarity between a text embedding and all samples of a collection.

    Filters are not applied. Returns null if the collection has no sample embeddings of its
    default embedding model.
    """
    return similarity_range_resolver.get_similarity_range(
        session=session, collection_id=collection_id, text_embedding=body.text_embedding
    )
