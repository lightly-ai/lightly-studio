"""This module contains the API routes for managing image embedding."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import Path as FastAPIPath
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_INTERNAL_SERVER_ERROR
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)

logger = logging.getLogger(__name__)

image_embedding_router = APIRouter()
EmbeddingManagerDep = Annotated[
    EmbeddingManager,
    Depends(lambda: EmbeddingManagerProvider.get_embedding_manager()),
]


@image_embedding_router.post(
    "/image_embedding/from_file/for_collection/{collection_id}", response_model=List[float]
)
def embed_image_from_file(
    embedding_manager: EmbeddingManagerDep,
    collection_id: Annotated[UUID, FastAPIPath(title="The ID of the collection.")],
    file: Annotated[UploadFile, File(description="The image file to embed.")],
    embedding_model_id: Annotated[
        UUID | None,
        Query(description="The ID of the embedding model to use."),
    ] = None,
) -> list[float]:
    """Retrieve embeddings for the uploaded image file."""
    try:
        suffix = Path(file.filename).suffix if file.filename else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            return embedding_manager.compute_image_embedding(
                collection_id=collection_id,
                filepath=tmp_path,
                embedding_model_id=embedding_model_id,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

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
