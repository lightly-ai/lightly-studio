"""This module contains the API routes for managing text embedding."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
)
from lightly_studio.embed.manager import (
    EmbedderManager,
    EmbedderManagerProvider,
)

text_embedding_router = APIRouter()
# Define a type alias for the EmbedderManager dependency
EmbedderManagerDep = Annotated[
    EmbedderManager,
    Depends(lambda: EmbedderManagerProvider.get_embedder_manager()),  # noqa: PLW0108
]


@text_embedding_router.get(
    "/text_embedding/for_collection/{collection_id}", response_model=list[float]
)
def embed_text(
    embedder_manager: EmbedderManagerDep,
    collection_id: Annotated[  # noqa: ARG001
        UUID, Path(title="The ID of the collection for which to embed.")
    ],
    query_text: str = Query(..., description="The text to embed."),
    embedding_model_id: Annotated[  # noqa: ARG001
        UUID | None,
        Query(..., description="The ID of the embedding model to use."),
    ] = None,
) -> list[float]:
    """Retrieve embeddings for the input text.

    The new ``EmbedderManager`` holds a single default text embedder in its
    registry, so ``collection_id`` and ``embedding_model_id`` are accepted for API
    compatibility but not used to select the model.
    """
    try:
        text_embeddings = embedder_manager.embed_text(text=query_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            detail=f"{exc}",
        ) from None

    return text_embeddings
