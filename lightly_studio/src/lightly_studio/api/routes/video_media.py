"""Video serving endpoint that supports multiple formats."""

from __future__ import annotations

import os
from collections.abc import Generator

import fsspec
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status
from lightly_studio.db_manager import SessionDep
from lightly_studio.resolvers import video_resolver

app_router = APIRouter(prefix="/videos/media")


@app_router.get("/{sample_id}")
async def serve_video_by_sample_id(
    sample_id: str,
    session: SessionDep,
) -> StreamingResponse:
    """Serve a video by sample ID."""
    sample_record = video_resolver.get_by_id(session=session, sample_id=sample_id)
    if not sample_record:
        raise HTTPException(
            status_code=status.HTTP_STATUS_NOT_FOUND,
            detail=f"Video sample not found: {sample_id}",
        )

    file_path = sample_record.file_path_abs
    content_type = _get_content_type(file_path)

    try:
        fs, fs_path = fsspec.core.url_to_fs(file_path)

        def file_stream() -> Generator[bytes, None, None]:
            with fs.open(fs_path, "rb") as f:
                chunk_size = 1024 * 1024
                while chunk := f.read(chunk_size):
                    yield chunk

        return StreamingResponse(
            file_stream(),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(fs.size(fs_path)),
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
