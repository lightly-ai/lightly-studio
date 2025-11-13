"""Video serving endpoint that supports multiple formats."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import fsspec
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status
from lightly_studio.db_manager import SessionDep
from lightly_studio.models import video

app_router = APIRouter(prefix="/videos/media")


def _parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """Parse the Range header and return (start, end) byte positions.

    Args:
        range_header: The Range header value (e.g., "bytes=0-1023")
        file_size: The total size of the file in bytes.

    Returns:
        Tuple of (start, end) byte positions, or None if range is invalid.
    """
    if not range_header or not range_header.startswith("bytes="):
        return None

    try:
        range_spec = range_header[6:]  # Remove "bytes=" prefix
        if "-" not in range_spec:
            return None

        start_str, end_str = range_spec.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1

        # Validate range
        if start < 0 or end >= file_size or start > end:
            return None

        return (start, end)
    except (ValueError, AttributeError):
        return None


async def _stream_file_range(
    fs: fsspec.AbstractFileSystem,
    fs_path: str,
    start: int,
    end: int,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    """Stream a specific byte range from a file.

    Args:
        fs: The filesystem instance.
        fs_path: The path to the file.
        start: Start byte position.
        end: End byte position.
        request: FastAPI request object for disconnect detection.
    """
    content_length = end - start + 1
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with fs.open(fs_path, "rb") as f:
            f.seek(start)
            remaining = content_length

            while remaining > 0:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                read_size = min(chunk_size, remaining)
                chunk = f.read(read_size)
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)
    except Exception:
        # Handle file read errors gracefully
        pass


async def _stream_full_file(
    fs: fsspec.AbstractFileSystem,
    fs_path: str,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    """Stream the entire file.

    Args:
        fs: The filesystem instance.
        fs_path: The path to the file.
        request: FastAPI request object for disconnect detection.
    """
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with fs.open(fs_path, "rb") as f:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception:
        # Handle file read errors gracefully
        pass


@app_router.get("/{sample_id}")
async def serve_video_by_sample_id(
    sample_id: str,
    session: SessionDep,
    request: Request,
    range_header: str | None = Header(None, alias="range"),
) -> StreamingResponse:
    """Serve a video by sample ID with HTTP Range request support.

    This endpoint supports HTTP Range requests, which are essential for
    efficient video streaming. Browsers use Range requests to:
    - Load only the necessary byte ranges
    - Enable seeking without downloading the entire file
    - Support multiple concurrent requests

    Args:
        sample_id: The ID of the video sample.
        session: Database session dependency (closed when function returns, before streaming).
        request: FastAPI request object.
        range_header: The HTTP Range header value.

    Returns:
        StreamingResponse with the video data, supporting partial content.
    """
    # Get sample record and close session early to avoid blocking
    sample_record = session.get(video.VideoTable, sample_id)
    if not sample_record:
        raise HTTPException(
            status_code=status.HTTP_STATUS_NOT_FOUND,
            detail=f"Video sample not found: {sample_id}",
        )

    file_path = sample_record.file_path_abs
    content_type = _get_content_type(file_path)

    # Extract file_path (a string) before returning StreamingResponse.
    # FastAPI's dependency system will close the session when this function returns,
    # which happens immediately after creating the StreamingResponse (before streaming starts).
    # This ensures the DB connection isn't held during the async streaming operation.

    try:
        fs, fs_path = fsspec.core.url_to_fs(file_path)
        file_size = fs.size(fs_path)

        # Parse range header if present
        range_tuple = _parse_range_header(range_header, file_size)

        if range_tuple:
            # Partial content request
            start, end = range_tuple
            content_length = end - start + 1

            return StreamingResponse(
                _stream_file_range(fs, fs_path, start, end, request),
                status_code=206,  # Partial Content
                media_type=content_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Cache-Control": "public, max-age=3600",
                },
            )

        # Full file request
        return StreamingResponse(
            _stream_full_file(fs, fs_path, request),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=3600",
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
