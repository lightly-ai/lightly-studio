"""Route to serve a single camera frame from a recording, by channel and keyframe timestamp."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY
from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.services.recording_service.get_camera_frame import (
    get_camera_frame as get_camera_frame_service,
)

get_camera_frame_router = APIRouter()


class CameraFrameQuery(BaseModel):
    """Query parameters selecting a camera frame."""

    channel_id: int = Query(description="The camera channel to read.")
    keyframe_timestamp_ns: int = Query(
        ge=0,
        description=(
            "The log time of the keyframe to fetch, in nanoseconds. "
            "Comes from the indexed locator's `keyframe_log_time_ns`."
        ),
    )
    w: int | None = Query(default=None, gt=0, description="Output width in pixels.")
    h: int | None = Query(default=None, gt=0, description="Output height in pixels.")
    q: int = Query(
        default=JPEG_QUALITY,
        ge=1,
        le=95,
        description="JPEG quality (1-95).",
    )


@get_camera_frame_router.get("/camera-frame")
def get_camera_frame(
    request: Request,
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    recording_id: Annotated[UUID, Path(title="Recording ID")],
    frame_query: Annotated[CameraFrameQuery, Depends(CameraFrameQuery)],
) -> Response:
    """Serves a camera keyframe from a recording, as a raw image.

    Returns the frame's encoded bytes directly, with the matching `Content-Type` (e.g.
    `image/jpeg`), so this route's own URL can be used as an `<img src="">` without any
    further decoding on the client.

    Args:
        request: The incoming HTTP request, used to read conditional-request headers.
        session: The database session.
        dataset_id: The dataset the recording is expected to belong to.
        recording_id: The recording to read the frame from.
        frame_query: The channel and keyframe timestamp to fetch.

    Returns:
        The encoded image, as the raw response body.

    Raises:
        HTTPException: 404 if the recording does not exist, does not belong to
            `dataset_id`, the channel is not in the recording's file, or no frame
            exists at `keyframe_timestamp_ns`.
    """
    try:
        frame = get_camera_frame_service(
            session=session,
            dataset_id=dataset_id,
            recording_id=recording_id,
            channel_id=frame_query.channel_id,
            keyframe_timestamp_ns=frame_query.keyframe_timestamp_ns,
            width=frame_query.w,
            height=frame_query.h,
            quality=frame_query.q,
        )
    except (ChannelNotFoundError, McapAccessError) as exc:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=str(exc)) from exc
    if frame is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=(
                f"No frame at keyframe timestamp {frame_query.keyframe_timestamp_ns} "
                f"on channel {frame_query.channel_id} of "
                f"recording {recording_id} in dataset {dataset_id}."
            ),
        )
    etag = f'"{frame.log_time_ns}-{frame_query.channel_id}"'
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and any(token.strip() in {"*", etag} for token in if_none_match.split(",")):
        return Response(status_code=304)
    return Response(
        content=frame.data,
        media_type=frame.media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Length": str(len(frame.data)),
            "ETag": etag,
            "X-Frame-Log-Time-Ns": str(frame.log_time_ns),
        },
    )
