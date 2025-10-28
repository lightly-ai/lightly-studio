"""Image serving endpoint that supports local files."""

from __future__ import annotations

import os
from collections.abc import Generator

import fsspec
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status
from lightly_studio.db_manager import SessionDep
from lightly_studio.models import image

app_router = APIRouter()


@app_router.get("/sample/{sample_id}")
async def serve_image_by_sample_id(
    sample_id: str,
    session: SessionDep,
) -> StreamingResponse:
    """Serve an image by sample ID.

    Args:
        sample_id: The ID of the sample.
        session: Database session.

    Returns:
        StreamingResponse with the image data.

    Raises:
        HTTPException: If the sample is not found or the file is not accessible.
    """
    # Retrieve the sample from the database.
    sample_record = session.get(image.ImageTable, sample_id)
    if not sample_record:
        raise HTTPException(
            status_code=status.HTTP_STATUS_NOT_FOUND,
            detail=f"Sample not found: {sample_id}",
        )

    file_path = sample_record.file_path_abs

    try:
        # Open the file.
        fs, fs_path = fsspec.core.url_to_fs(file_path)
        content = fs.cat_file(fs_path)

        # Determine content type based on file extension.
        content_type = _get_content_type(file_path)

        # Create a streaming response.
        def generate() -> Generator[bytes, None, None]:
            yield content

        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={
                # Cache for 1 hour
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(content)),
            },
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_STATUS_NOT_FOUND,
            detail=f"File not found: {file_path}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_STATUS_NOT_FOUND,
            detail=f"Error accessing file {file_path}: {exc.strerror}",
        ) from exc


def _get_content_type(file_path: str) -> str:
    """Get the appropriate content type for a file based on its extension.

    Args:
        file_path: Path to the file.

    Returns:
        MIME type string.
    """
    ext = os.path.splitext(file_path)[1].lower()

    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".mov": "video/quicktime",
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
    }

    return content_types.get(ext, "application/octet-stream")
