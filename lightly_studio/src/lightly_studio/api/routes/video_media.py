"""Video serving endpoint that supports multiple formats."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import fsspec
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from lightly_studio.api.routes import s3_media
from lightly_studio.api.routes.api import status
from lightly_studio.database import db_manager
from lightly_studio.models import video
from lightly_studio.utils.executor import get_media_executor

app_router = APIRouter(prefix="/videos/media")


@dataclass(frozen=True)
class RangeRequest:
    """The result of parsing a single HTTP byte range request."""

    start: int | None = None
    end: int | None = None
    is_unsatisfiable: bool = False


def _parse_range_header(range_header: str | None, file_size: int) -> RangeRequest:
    """Parse the Range header and return (start, end) byte positions.

    Args:
        range_header: The Range header value (e.g., "bytes=0-1023")
        file_size: The total size of the file in bytes.

    Returns:
        The requested byte range, or an unsatisfiable result. Unsupported ranges
        return an empty result and retain full-file delivery.
    """
    if not range_header or not range_header.startswith("bytes="):
        return RangeRequest()

    range_spec = range_header[6:]
    if "," in range_spec:
        return RangeRequest()

    start_str, separator, end_str = range_spec.partition("-")
    if not separator or (not start_str and not end_str):
        return RangeRequest(is_unsatisfiable=True)

    try:
        if not start_str:
            return _parse_suffix_range(end_str=end_str, file_size=file_size)
        return _parse_explicit_range(
            start_str=start_str,
            end_str=end_str,
            file_size=file_size,
        )
    except ValueError:
        return RangeRequest(is_unsatisfiable=True)


def _parse_suffix_range(end_str: str, file_size: int) -> RangeRequest:
    """Parse a suffix byte range."""
    suffix_length = int(end_str)
    if suffix_length <= 0 or file_size == 0:
        return RangeRequest(is_unsatisfiable=True)
    return RangeRequest(start=max(file_size - suffix_length, 0), end=file_size - 1)


def _parse_explicit_range(start_str: str, end_str: str, file_size: int) -> RangeRequest:
    """Parse a closed or open-ended byte range."""
    start = int(start_str)
    if start < 0 or start >= file_size:
        return RangeRequest(is_unsatisfiable=True)

    end = file_size - 1 if not end_str else min(int(end_str), file_size - 1)
    if end < start:
        return RangeRequest(is_unsatisfiable=True)
    return RangeRequest(start=start, end=end)


def _get_filesystem_and_size(file_path: str) -> tuple[fsspec.AbstractFileSystem, str, int]:
    """Resolve a video path and its size outside the event loop."""
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    return fs, fs_path, fs.size(fs_path)


def _open_file(fs: fsspec.AbstractFileSystem, fs_path: str) -> Any:
    """Open a file for streaming outside the event loop."""
    return fs.open(fs_path, "rb")


def _read_file_chunk(file: Any, size: int) -> bytes:
    """Read a chunk from an open file outside the event loop."""
    return file.read(size)


def _seek_file(file: Any, start: int) -> None:
    """Seek an open file outside the event loop."""
    file.seek(start)


def _close_file(file: Any) -> None:
    """Close an open file outside the event loop."""
    file.close()


async def _stream_file(
    fs: fsspec.AbstractFileSystem,
    fs_path: str,
    start: int,
    content_length: int,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    """Stream a file or byte range without blocking the event loop.

    Args:
        fs: The filesystem instance.
        fs_path: The path to the file.
        start: Start byte position.
        content_length: Number of bytes to stream.
        request: FastAPI request object for disconnect detection.
    """
    chunk_size = 1024 * 1024  # 1MB chunks
    loop = asyncio.get_running_loop()
    executor = get_media_executor("video_media")
    file = await loop.run_in_executor(executor, _open_file, fs, fs_path)
    try:
        if start:
            await loop.run_in_executor(executor, _seek_file, file, start)

        remaining = content_length
        while remaining > 0:
            if await request.is_disconnected():
                break

            read_size = min(chunk_size, remaining)
            chunk = await loop.run_in_executor(executor, _read_file_chunk, file, read_size)
            if not chunk:
                raise OSError("Video stream ended before the declared content length")
            yield chunk
            remaining -= len(chunk)
    finally:
        await loop.run_in_executor(executor, _close_file, file)


@app_router.get("/{sample_id}")
async def serve_video_by_sample_id(
    sample_id: str,
    request: Request,
    range_header: str | None = Header(None, alias="range"),
    mode: s3_media.MediaDeliveryMode | None = None,
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
        mode: Explicit media-delivery override.

    Returns:
        StreamingResponse with the video data, supporting partial content.
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

    content_type = _get_content_type(file_path)
    if mode is None:
        redirect = await s3_media.create_s3_media_redirect(
            file_path=file_path,
            content_type=content_type,
        )
        if redirect is not None:
            return redirect

    try:
        fs, fs_path, file_size = await asyncio.get_running_loop().run_in_executor(
            get_media_executor("video_media"),
            _get_filesystem_and_size,
            file_path,
        )

        # Parse range header if present
        range_request = _parse_range_header(range_header, file_size)

        if range_request.is_unsatisfiable:
            return StreamingResponse(
                content=iter(()),
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        if range_request.start is not None and range_request.end is not None:
            # Partial content request
            start, end = range_request.start, range_request.end
            content_length = end - start + 1

            return StreamingResponse(
                _stream_file(fs, fs_path, start, content_length, request),
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
            _stream_file(fs, fs_path, 0, file_size, request),
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
