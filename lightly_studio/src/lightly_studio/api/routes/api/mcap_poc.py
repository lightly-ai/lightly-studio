"""Proof-of-concept routes for comparing MCAP point-cloud processing paths."""

from typing import Annotated
from urllib import parse

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NO_CONTENT
from lightly_studio.dataset import env
from lightly_studio.integrations.mcap_poc import reader

mcap_poc_router = APIRouter(prefix="/mcap-poc", tags=["mcap poc"])


class McapPocTopicView(BaseModel):
    """Indexed point-cloud topic available to the PoC."""

    topic: str
    message_count: int
    first_log_time_ns: str


class McapPocSourceView(BaseModel):
    """Configured MCAP source and browser-direct access details."""

    direct_url: str
    size_bytes: int
    version: str
    topics: list[McapPocTopicView]


@mcap_poc_router.get("/source", response_model=McapPocSourceView)
def get_mcap_poc_source(request: Request) -> McapPocSourceView:
    """Return the configured MCAP source and indexed point-cloud topics."""
    source = _configured_source()
    description = reader.describe_source(source=source)
    direct_url = _direct_url(source=source, request=request)
    return McapPocSourceView(
        direct_url=direct_url,
        size_bytes=description.size_bytes,
        version=description.version,
        topics=[
            McapPocTopicView(
                topic=topic.topic,
                message_count=topic.message_count,
                first_log_time_ns=str(topic.first_log_time_ns),
            )
            for topic in description.topics
        ],
    )


@mcap_poc_router.api_route("/source/content", methods=["GET", "HEAD"], name="serve_mcap_poc_source")
def serve_mcap_poc_source() -> FileResponse:
    """Serve a local PoC source with HTTP range support."""
    path = reader.local_source_path(source=_configured_source())
    if path is None:
        raise ValueError("Remote MCAP sources are read directly by the browser.")
    return FileResponse(path=path, media_type="application/octet-stream")


@mcap_poc_router.get("/frame")
def get_mcap_poc_frame(
    topic: Annotated[str, Query(min_length=1)],
    timestamp_ns: Annotated[int, Query(ge=0)],
    reuse_index: Annotated[bool, Query()] = True,
) -> Response:
    """Decode one frame on the backend and return packed float32 XYZI points."""
    result = reader.read_point_cloud_frame(
        source=_configured_source(),
        topic=topic,
        timestamp_ns=timestamp_ns,
        reuse_index=reuse_index,
    )
    headers = {
        "Cache-Control": "no-store",
        "X-MCAP-Point-Count": str(result.point_count),
        "X-MCAP-Point-Stride": "16",
        "X-MCAP-Log-Time-Ns": str(result.log_time_ns),
        "X-MCAP-Source-Bytes": str(result.bytes_read),
        "X-MCAP-Read-Count": str(result.read_count),
        "X-MCAP-Backend-Wall-Ms": f"{result.wall_time_ms:.3f}",
        "X-MCAP-Backend-Index-Ms": f"{result.index_time_ms:.3f}",
        "X-MCAP-Backend-Decode-Ms": f"{result.decode_time_ms:.3f}",
        "X-MCAP-Backend-Cpu-Ms": f"{result.cpu_time_ms:.3f}",
        "X-MCAP-Backend-Peak-Bytes": str(result.peak_memory_bytes),
        "X-MCAP-Index-Cached": "1" if result.index_cached else "0",
    }
    return Response(content=result.content, media_type="application/octet-stream", headers=headers)


@mcap_poc_router.post("/reset")
def reset_mcap_poc_cache() -> Response:
    """Drop the cached summary index so the next frame request measures a cold read."""
    reader.clear_source_cache()
    return Response(status_code=HTTP_STATUS_NO_CONTENT)


def _configured_source() -> str:
    source = env.LIGHTLY_STUDIO_MCAP_POC_SOURCE
    if not source:
        raise ValueError("Set LIGHTLY_STUDIO_MCAP_POC_SOURCE to enable the MCAP PoC.")
    return source


def _direct_url(source: str, request: Request) -> str:
    if parse.urlparse(source).scheme in ("http", "https"):
        return source
    return str(request.url_for("serve_mcap_poc_source"))
