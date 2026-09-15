"""Serve a recording by ID."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import recording_resolver
from lightly_studio.utils import byte_range

recording_router = APIRouter(prefix="/recordings")


@recording_router.get("/{recording_id}")
def get_recording(
    recording_id: UUID,
    request: Request,
    range_header: str | None = Header(
        None, alias="range", description="Byte range to serve (RFC 9110)."
    ),
    if_match: str | None = Header(
        None, alias="if-match", description="Precondition ETag list (RFC 9110)."
    ),
) -> Response:
    """Serve a dataset recording from its local or object-storage URI.

    Supports partial content via the ``Range`` header (HTTP 206) and
    conditional requests via ``If-Match`` (HTTP 412 on mismatch).
    """
    with db_manager.session() as session:
        recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise NotFoundError(f"Recording not found: {recording_id}")
    try:
        info = byte_range.file_info(file_path=recording.uri)
        return byte_range.serve_file(
            info=info,
            request=request,
            range_header=range_header,
            media_type="application/octet-stream",
            if_match=if_match,
        )
    except FileNotFoundError as error:
        raise NotFoundError(f"Recording not found: {recording.uri}") from error
