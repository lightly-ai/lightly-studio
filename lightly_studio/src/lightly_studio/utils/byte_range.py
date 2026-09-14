"""Byte-range file serving and file metadata helpers shared by media endpoints."""

from __future__ import annotations

import hashlib
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
    etag: str


def file_info(file_path: str) -> FileInfo:
    """Return size and ETag for a local or remote file."""
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    info = fs.info(fs_path)
    size_bytes = int(info["size"])
    return FileInfo(size_bytes=size_bytes, etag=_revision(info=info, file_size=size_bytes))


def serve_file(
    *,
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
    revision = _revision(info=info, file_size=file_size)
    if if_match is not None and if_match.strip('"') != revision:
        return Response(status_code=status.HTTP_STATUS_PRECONDITION_FAILED)

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
        "ETag": f'"{revision}"',
    }
    byte_range = parse_range_header(range_header=range_header, file_size=file_size)
    if byte_range is None:
        return StreamingResponse(
            _stream(fs=fs, fs_path=fs_path, start=0, size=file_size, request=request),
            media_type=media_type,
            headers={**headers, "Content-Length": str(file_size)},
        )

    start, end = byte_range
    size = end - start + 1
    return StreamingResponse(
        _stream(fs=fs, fs_path=fs_path, start=start, size=size, request=request),
        status_code=status.HTTP_STATUS_PARTIAL_CONTENT,
        media_type=media_type,
        headers={
            **headers,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(size),
        },
    )


def parse_range_header(*, range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """Parse a single inclusive byte range, returning ``None`` when invalid."""
    if not range_header or not range_header.startswith("bytes="):
        return None
    range_spec = range_header[len("bytes=") :]
    if "-" not in range_spec:
        return None
    start_str, end_str = range_spec.split("-", 1)
    try:
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        return None
    if start < 0 or end >= file_size or start > end:
        return None
    return start, end


async def _stream(
    *,
    fs: fsspec.AbstractFileSystem,
    fs_path: str,
    start: int,
    size: int,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    remaining = size
    with fs.open(fs_path, "rb") as handle:
        handle.seek(start)
        while remaining > 0:
            chunk = handle.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                return
            yield chunk
            remaining -= len(chunk)
            if remaining > 0 and await request.is_disconnected():
                return


def _revision(*, info: Mapping[str, Any], file_size: int) -> str:
    """Return a stable opaque revision token for a local or remote file."""
    etag = info.get("ETag") or info.get("etag")
    if isinstance(etag, str) and etag:
        return etag.strip('"')
    for key in ("mtime", "LastModified", "last_modified"):
        modified = info.get(key)
        if modified is not None:
            return hashlib.sha256(f"{file_size}-{modified}".encode()).hexdigest()[:32]
    return str(file_size)
