"""MCAP recording serving with HTTP range support."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from lightly_studio.api.routes import byte_range
from lightly_studio.core.mcap import recording_source
from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError

app_router = APIRouter(prefix="/mcap/media")

_MEDIA_TYPE = "application/octet-stream"


@app_router.get("/{sample_id}")
def serve_mcap_recording_by_sample_id(
    sample_id: UUID,
    request: Request,
    range_header: str | None = Header(None, alias="range"),
    if_match: str | None = Header(None, alias="if-match"),
) -> Response:
    """Serve the recording an MCAP sample points into, one byte range per request.

    Point-cloud frames are decoded in the browser, which reads an indexed recording by
    seeking: a few kilobytes of index, then the one chunk holding the requested message.
    That is why this serves byte ranges of the recording rather than decoded frames.

    Args:
        sample_id: The MCAP sample whose recording to serve.
        request: FastAPI request object.
        range_header: The HTTP ``Range`` header value.
        if_match: The HTTP ``If-Match`` header value, used to pin one recording revision
            across the many range requests that reading a frame takes.

    Returns:
        The requested byte range of the recording, or the whole recording when no range
        was asked for.

    Raises:
        NotFoundError: No such MCAP sample, no recording configured for it, or the
            configured recording is missing.
    """
    # Avoid SessionDep here: FastAPI runs its sync-generator dependency on Starlette's
    # threadpool, exhausting threadpool slots under load. Manage the session inline and
    # close it before any file I/O.
    with db_manager.session() as session:
        recording_path = recording_source.resolve_recording_path(
            session=session, sample_id=sample_id
        )

    try:
        return byte_range.serve_file(
            file_path=recording_path,
            request=request,
            range_header=range_header,
            media_type=_MEDIA_TYPE,
            if_match=if_match,
        )
    except FileNotFoundError as error:
        raise NotFoundError(f"Recording not found: {recording_path}") from error
