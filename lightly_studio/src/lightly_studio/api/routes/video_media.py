"""Video serving endpoint that supports multiple formats."""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Request, Response

from lightly_studio.api.routes import byte_range
from lightly_studio.api.routes.api import status
from lightly_studio.database import db_manager
from lightly_studio.models import video

app_router = APIRouter(prefix="/videos/media")


@app_router.get("/{sample_id}")
def serve_video_by_sample_id(
    sample_id: str,
    request: Request,
    range_header: str | None = Header(None, alias="range"),
) -> Response:
    """Serve a video by sample ID with HTTP Range request support.

    This endpoint supports HTTP Range requests, which are essential for
    efficient video streaming. Browsers use Range requests to:
    - Load only the necessary byte ranges
    - Enable seeking without downloading the entire file
    - Support multiple concurrent requests

    Args:
        sample_id: The ID of the video sample.
        request: FastAPI request object.
        range_header: The HTTP Range header value.

    Returns:
        The requested byte range of the video, or the whole video when no range was
        asked for.
    """
    # Avoid SessionDep here: FastAPI runs its sync-generator dependency on
    # Starlette's threadpool, exhausting threadpool slots under load. Manage
    # the session inline and close it before any file I/O.
    with db_manager.session() as sess:
        sample_record = sess.get(video.VideoTable, sample_id)
        if not sample_record:
            raise HTTPException(
                status_code=status.HTTP_STATUS_NOT_FOUND,
                detail=f"Video sample not found: {sample_id}",
            )
        file_path = sample_record.file_path_abs

    try:
        return byte_range.serve_file(
            file_path=file_path,
            request=request,
            range_header=range_header,
            media_type=_get_content_type(file_path),
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
    """Get the appropriate content type for a video file based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv",
        ".mpeg": "video/mpeg",
        ".mpg": "video/mpeg",
        ".3gp": "video/3gpp",
        ".ts": "video/mp2t",
        ".m4v": "video/x-m4v",
    }
    return content_types.get(ext, "application/octet-stream")
