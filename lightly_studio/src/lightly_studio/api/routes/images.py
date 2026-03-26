"""Image serving endpoint that supports local files."""

from __future__ import annotations

import io
import os
from collections.abc import Generator

import cv2
import fsspec
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status
from lightly_studio.db_manager import SessionDep
from lightly_studio.models import image

app_router = APIRouter()


@app_router.get("/sample/{sample_id}")
async def serve_image_by_sample_id(
    sample_id: str,
    session: SessionDep,
    max_size: int | None = Query(None, description="Maximum dimension (width or height) in pixels"),
) -> StreamingResponse:
    """Serve an image by sample ID.

    Args:
        sample_id: The ID of the sample.
        session: Database session.
        max_size: Optional maximum dimension (width or height) in pixels. If provided,
                  the image will be resized proportionally to fit within this constraint.

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
        is_image = content_type.startswith("image/")

        # Resize image if max_size is provided and file is an image.
        if max_size is not None and is_image:
            content = _resize_image(content, max_size, content_type)

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


def _resize_image(image_bytes: bytes, max_size: int, content_type: str) -> bytes:
    """Resize an image proportionally to fit within max_size constraint.

    Args:
        image_bytes: The original image bytes.
        max_size: Maximum dimension (width or height) in pixels.
        content_type: MIME type of the image.

    Returns:
        Resized image bytes.
    """
    # Decode image from bytes.
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

    if img is None:
        # If decoding fails, return original bytes.
        return image_bytes

    # Get current dimensions.
    height, width = img.shape[:2]

    # Calculate new dimensions while maintaining aspect ratio.
    if width > height:
        if width > max_size:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            return image_bytes  # No resizing needed
    else:
        if height > max_size:
            new_height = max_size
            new_width = int(width * (max_size / height))
        else:
            return image_bytes  # No resizing needed

    # Resize image.
    resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # Encode back to bytes based on content type.
    ext = _get_extension_from_content_type(content_type)
    success, encoded_img = cv2.imencode(ext, resized_img)

    if not success:
        # If encoding fails, return original bytes.
        return image_bytes

    return encoded_img.tobytes()


def _get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from content type for cv2.imencode.

    Args:
        content_type: MIME type string.

    Returns:
        File extension string (e.g., '.png', '.jpg').
    """
    type_to_ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
    }
    return type_to_ext.get(content_type, ".jpg")


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
