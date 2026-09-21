"""This module contains the API routes for managing image embedding."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi import Path as FastAPIPath

from lightly_studio.api.routes.api.status import HTTP_STATUS_INTERNAL_SERVER_ERROR
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.embed import embed_samples

logger = logging.getLogger(__name__)

image_embedding_router = APIRouter()


@image_embedding_router.post(
    "/image_embedding/from_file/for_collection/{collection_id}", response_model=list[float]
)
def embed_image_from_file(
    session: SessionDep,
    collection_id: Annotated[UUID, FastAPIPath(title="The ID of the collection.")],
    file: Annotated[UploadFile, File(description="The image file to embed.")],
    embedding_model_id: Annotated[
        UUID | None,
        Query(description="The ID of the embedding model to use."),
    ] = None,
) -> list[float]:
    """Retrieve embeddings for the uploaded image file."""
    if embedding_model_id is not None:
        raise NotImplementedError(
            "Per-request embedding model override is not supported yet. Collection's "
            "default embedding model is always used."
        )
    try:
        return embed_samples.embed_image_for_collection(
            session=session, collection_id=collection_id, image_bytes=file.file.read()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            detail=f"{exc}",
        ) from None
    except Exception as exc:
        logger.exception("Error processing image from file")
        raise HTTPException(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {exc}",
        ) from None
