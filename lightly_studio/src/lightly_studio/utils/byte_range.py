"""Byte-range file serving and file metadata helpers shared by media endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass
from typing import Any

import fsspec
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status

_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileInfo:
    """Size and ETag for a local or remote file."""

    size_bytes: int
    etag: str | None


def file_info(file_path: str) -> FileInfo:
    """Return size and ETag for a local or remote file."""
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    info = fs.info(fs_path)
    size_bytes = int(info["size"])
    return FileInfo(size_bytes=size_bytes, etag=_revision(info=info))


def serve_file(
    file_path: str,
    request: Request,
    range_header: str | None,
    media_type: str,
    if_match: str | None = None,
) -> Response:
    """Serve a file whole or as the requested byte range."""
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    info = fs.info(fs_path)
    file_size = int(info["size"])
    revision = _revision(info=info)
    if (
        revision is not None
        and if_match is not None
        and not _if_match_satisfied(if_match=if_match, revision=revision)
    ):
        return Response(status_code=status.HTTP_STATUS_PRECONDITION_FAILED)

    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }
    if revision is not None:
        headers["ETag"] = f'"{revision}"'
    byte_range = parse_range_header(range_header=range_header, file_size=file_size)
    if range_header is not None and range_header.startswith("bytes=") and byte_range is None:
        return Response(
            status_code=status.HTTP_STATUS_RANGE_NOT_SATISFIABLE,
            headers={**headers, "Content-Range": f"bytes */{file_size}"},
        )
    handle = fs.open(fs_path, "rb")
    if byte_range is None:
        return StreamingResponse(
            _stream(handle=handle, start=0, size=file_size, request=request),
            media_type=media_type,
            headers={**headers, "Content-Length": str(file_size)},
        )

    start, end = byte_range
    size = end - start + 1
    return StreamingResponse(
        _stream(handle=handle, start=start, size=size, request=request),
        status_code=status.HTTP_STATUS_PARTIAL_CONTENT,
        media_type=media_type,
        headers={
            **headers,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(size),
        },
    )


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """Parse a single inclusive byte range, returning ``None`` when invalid."""
    if not range_header or not range_header.startswith("bytes="):
        return None
    range_spec = range_header[len("bytes=") :].strip()
    if "-" not in range_spec:
        return None
    start_str, end_str = range_spec.split("-", 1)
    return _parse_range_spec(start_str=start_str, end_str=end_str, file_size=file_size)


def _parse_range_spec(start_str: str, end_str: str, file_size: int) -> tuple[int, int] | None:
    """Parse the two components of a single byte range."""
    try:
        if not start_str:
            suffix_size = int(end_str)
            if suffix_size <= 0 or file_size == 0:
                return None
            return max(file_size - suffix_size, 0), file_size - 1
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        return None
    if start < 0 or start >= file_size or end < start:
        return None
    return start, min(end, file_size - 1)


async def _stream(
    handle: Any,
    start: int,
    size: int,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    remaining = size
    try:
        await asyncio.to_thread(handle.seek, start)
        while remaining > 0:
            if await request.is_disconnected():
                return
            chunk = await asyncio.to_thread(handle.read, min(_CHUNK_SIZE, remaining))
            if not chunk:
                return
            yield chunk
            remaining -= len(chunk)
    finally:
        await asyncio.to_thread(handle.close)


def _revision(*, info: Mapping[str, Any]) -> str | None:
    """Return a stable opaque revision token for a local or remote file."""
    for key in ("ETag", "etag", "VersionId", "version_id", "generation", "Generation"):
        revision = info.get(key)
        if isinstance(revision, str) and revision:
            return revision.strip('"')
    return None


def _if_match_satisfied(*, if_match: str, revision: str) -> bool:
    """Return whether If-Match contains the current strong entity tag."""
    tags = [tag.strip() for tag in if_match.split(",")]
    if "*" in tags:
        return True
    return any(tag == f'"{revision}"' for tag in tags)
