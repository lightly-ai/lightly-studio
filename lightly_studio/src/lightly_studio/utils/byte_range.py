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
    """Size and ETag for a local or remote file.

    Attributes:
        path: The local or remote URI, passed to fsspec for opening.
        size_bytes: Total file size in bytes.
        etag: Opaque revision token from the storage backend, or ``None``
            when the backend does not provide one.
    """

    path: str
    size_bytes: int
    etag: str | None


def file_info(file_path: str) -> FileInfo:
    """Return path, size, and ETag for a local or remote file."""
    fs, fs_path = fsspec.core.url_to_fs(file_path)
    info = fs.info(fs_path)
    return FileInfo(
        path=file_path,
        size_bytes=int(info["size"]),
        etag=_revision(info=info),
    )


def serve_file(
    info: FileInfo,
    request: Request,
    range_header: str | None,
    media_type: str,
    if_match: str | None = None,
) -> Response:
    """Serve a file whole or as the requested byte range.

    Args:
        info: Metadata from :func:`file_info`. Callers fetch it once and pass
            it here so this function never issues a second stat.
        request: FastAPI request, used for disconnection detection.
        range_header: Value of the HTTP ``Range`` header.
        media_type: MIME type for the response.
        if_match: Value of the HTTP ``If-Match`` header.
    """
    fs, fs_path = fsspec.core.url_to_fs(info.path)
    file_size = info.size_bytes
    revision = info.etag
    if (
        if_match is not None
        and if_match.strip() != "*"
        and (revision is None or not _if_match_satisfied(if_match=if_match, revision=revision))
    ):
        return Response(status_code=status.HTTP_STATUS_PRECONDITION_FAILED)

    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }
    if revision is not None:
        headers["ETag"] = f'"{revision}"'
    byte_range = parse_range_header(range_header=range_header, file_size=file_size)
    if byte_range is None and _is_unsatisfiable(range_header=range_header, file_size=file_size):
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


def _is_unsatisfiable(*, range_header: str | None, file_size: int) -> bool:
    """Return whether range_header is a single byte range beyond the file end."""
    if not range_header or not range_header.startswith("bytes="):
        return False
    spec = range_header[len("bytes=") :].strip()
    # Multi-range (contains comma outside quotes) — not our concern, fall through.
    if "," in spec:
        return False
    if "-" not in spec:
        return False
    start_str, end_str = spec.split("-", 1)
    try:
        if not start_str:
            return False
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        return False
    return start >= file_size or end < start


def _if_match_satisfied(*, if_match: str, revision: str) -> bool:
    """Return whether If-Match contains the current strong entity tag.

    Parses commas that appear outside quoted strings so that ETags containing
    commas (e.g. ``"a,b"``) are matched correctly.
    """
    tags = _split_etag_list(if_match)
    return any(tag == f'"{revision}"' for tag in tags)


def _split_etag_list(value: str) -> list[str]:
    """Split a comma-separated ETag list, ignoring commas inside quoted strings."""
    tags: list[str] = []
    current: list[str] = []
    in_quotes = False
    for char in value:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
        elif char == "," and not in_quotes:
            tags.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        tags.append("".join(current).strip())
    return tags
