"""This module contains the API routes for managing text embedding."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.embed import embed_samples

text_embedding_router = APIRouter()


@text_embedding_router.get(
    "/text_embedding/for_collection/{collection_id}", response_model=list[float]
)
def embed_text(
    collection_id: Annotated[UUID, Path(title="The ID of the collection for which to embed.")],
    session: SessionDep,
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
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail=f"{exc}",
        ) from None

    return text_embeddings
