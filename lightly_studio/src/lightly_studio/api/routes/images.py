"""Image serving endpoint that supports local files."""

from __future__ import annotations

import io
import os
from collections.abc import Generator

import fsspec
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps, UnidentifiedImageError

from lightly_studio.api.routes.api import status
from lightly_studio.db_manager import SessionDep
from lightly_studio.models import image
from lightly_studio.models.settings import GridViewThumbnailQualityType

app_router = APIRouter()

JPEG_QUALITY = 75


@app_router.get("/sample/{sample_id}")
async def serve_image_by_sample_id(
    sample_id: str,
    session: SessionDep,
    quality: GridViewThumbnailQualityType = GridViewThumbnailQualityType.RAW,
    max_width: int | None = Query(default=None, ge=1),
    max_height: int | None = Query(default=None, ge=1),
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

        if quality == GridViewThumbnailQualityType.HIGH:
            content, content_type = _transform_image(
                content=content,
                max_width=max_width,
                max_height=max_height,
            )
        else:
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


def _transform_image(
    content: bytes,
    max_width: int | None,
    max_height: int | None,
) -> tuple[bytes, str]:
    """Resize and encode an image for grid thumbnails."""
    if max_width is None and max_height is None:
        raise HTTPException(
            status_code=status.HTTP_STATUS_BAD_REQUEST,
            detail="max_width or max_height is required when quality=high",
        )

    try:
        with Image.open(io.BytesIO(content)) as image_file:
            normalized_image = ImageOps.exif_transpose(image_file)
            resized = _resize_image(
                image=normalized_image,
                max_width=max_width,
                max_height=max_height,
            )
            if resized.mode not in ("RGB", "L"):
                resized = resized.convert("RGB")

            output = io.BytesIO()
            resized.save(
                output,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
            )
            return output.getvalue(), "image/jpeg"
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_STATUS_BAD_REQUEST,
            detail="Unsupported image file for thumbnail conversion",
        ) from exc


def _resize_image(
    image: Image.Image,
    max_width: int | None,
    max_height: int | None,
) -> Image.Image:
    """Resize image while preserving aspect ratio and avoiding upscaling."""
    max_width = max_width or image.width
    max_height = max_height or image.height
    scale = min(max_width / image.width, max_height / image.height, 1)

    if scale == 1:
        return image

    target_size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    return image.resize(target_size, Image.Resampling.LANCZOS)


def _get_content_type(file_path: str) -> str:
    """Get the appropriate content type for a file based on its extension."""
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
