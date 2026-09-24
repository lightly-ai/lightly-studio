"""This module contains the API routes for managing image embedding."""

from __future__ import annotations

import logging
from typing import IO, Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi import Path as FastAPIPath

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_PAYLOAD_TOO_LARGE,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.embed import embed_samples
from lightly_studio.embed.errors import QueryEmbedderError
from lightly_studio.embed.remote.errors import RemoteEmbedderError

logger = logging.getLogger(__name__)

image_embedding_router = APIRouter()

# An upload is held in memory to embed it, so a query image larger than this is refused
# instead of read
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
# An upload larger than this is embedded, but logged, since it uses much memory
_LARGE_UPLOAD_WARNING_BYTES = 20 * 1024 * 1024


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
    image_bytes = _read_at_most(stream=file.file, max_bytes=_MAX_UPLOAD_BYTES)
    if image_bytes is None:
        raise HTTPException(
            status_code=HTTP_STATUS_PAYLOAD_TOO_LARGE,
            detail=(
                f"The uploaded file is larger than {_MAX_UPLOAD_BYTES} bytes. "
                f"Uploaded file: {file.filename!r}."
            ),
        )
    if len(image_bytes) > _LARGE_UPLOAD_WARNING_BYTES:
        logger.warning(
            "The uploaded file %r is %d bytes, which is large for a query image.",
            file.filename,
            len(image_bytes),
        )
    try:
        return embed_samples.embed_image_for_collection(
            session=session, collection_id=collection_id, image_bytes=image_bytes
        )
    except embed_samples.ImageNotEmbeddedError as exc:
        # An upload the embedder drops is a broken image, so it is a bad request
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail=f"{exc} Uploaded file: {file.filename!r}.",
        ) from None
    # The app exception handlers map these
    except (QueryEmbedderError, RemoteEmbedderError):
        raise
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


def _read_at_most(stream: IO[bytes], max_bytes: int) -> bytes | None:
    """Read the stream, or return ``None`` if it holds more than ``max_bytes`` bytes."""
    data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        return None
    return data
