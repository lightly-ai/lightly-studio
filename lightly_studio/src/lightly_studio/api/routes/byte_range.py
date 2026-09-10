"""Byte-range file serving shared by the media endpoints.

Random access over HTTP is what lets a client read one frame out of a large recording,
or seek in a video, without downloading the whole file. Both media routes need the same
response shape, so they share it from here.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator, Mapping
from typing import Any

import fsspec
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from lightly_studio.api.routes.api import status

_CHUNK_SIZE = 1024 * 1024
# Recording and video bytes never change in place: a new revision is a new file, and the
# ETag below is what catches a caller holding a stale one.
_CACHE_CONTROL = "public, max-age=3600"


def serve_file(
    *,
    file_path: str,
    request: Request,
    range_header: str | None,
    media_type: str,
    if_match: str | None = None,
) -> Response:
    """Serve a file whole, or as the single byte range the client asked for.

    Args:
        file_path: Path or URL of the file, opened through fsspec.
        request: The request, used to stop streaming once the client disconnects.
        range_header: The request's ``Range`` header, when it sent one.
        media_type: Content type to report.
        if_match: The request's ``If-Match`` header. When it does not match the file's
            current revision, the file changed since the caller last read it and nothing
            is served, so a client cannot mix bytes from two versions of one file.

    Returns:
        Partial content for a valid range request, precondition failed for a stale
        ``If-Match``, and the whole file otherwise. Every response carries
        ``Accept-Ranges`` and an ``ETag``.

    Raises:
        FileNotFoundError: The file does not exist. Callers map this to their own
            not-found error, because what is missing differs per route.
    """
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    info = fs.info(fs_path)
    file_size = int(info["size"])
    revision = _revision(info=info, file_size=file_size)
    if if_match is not None and if_match.strip('"') != revision:
        return Response(status_code=status.HTTP_STATUS_PRECONDITION_FAILED)

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": _CACHE_CONTROL,
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
    """Parse a single-range ``Range`` header into inclusive byte positions.

    Args:
        range_header: The header value, for example ``bytes=0-1023``.
        file_size: Size of the file in bytes.

    Returns:
        The inclusive start and end positions, or None when the header is absent,
        malformed, or asks for bytes outside the file. An empty start is read as 0
        rather than as a suffix range, and only the first range is considered.
    """
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
    """Yield ``size`` bytes from ``start``, stopping early if the client goes away.

    The disconnect check comes after a chunk, never before one: a probe that answered wrongly
    would otherwise suppress the whole body, and a caller that asked for a handful of bytes
    would receive an empty response with a length header promising content.
    """
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
    """Return an opaque revision token for a file.

    Prefers the object store's own entity tag. Local filesystems report no tag, so their
    size and modification time are hashed instead, which keeps the token valid inside an
    ``ETag`` header whatever the filesystem reports.
    """
    etag = info.get("ETag") or info.get("etag")
    if isinstance(etag, str) and etag:
        return etag.strip('"')
    for key in ("mtime", "LastModified", "last_modified"):
        modified = info.get(key)
        if modified is not None:
            return hashlib.sha256(f"{file_size}-{modified}".encode()).hexdigest()[:32]
    return str(file_size)
