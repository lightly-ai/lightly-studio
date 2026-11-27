"""Route that returns the decoded point clouds and camera frames of one tick."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST
from lightly_studio.api.routes.mcap_sequences import tick_payload_encoding
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.services.recording_service import get_tick_data as get_tick_data_service

get_tick_data_router = APIRouter()


@get_tick_data_router.get(
    "/ticks/{seq_number}/data",
    responses={200: {"content": {tick_payload_encoding.MEDIA_TYPE: {}}}},
)
def get_tick_data(  # noqa: PLR0913
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    seq_number: Annotated[int, Path(title="Tick position, zero-based", ge=0)],
    target_frame_id: Annotated[
        str | None,
        Query(
            description=(
                "The coordinate frame to express the points in, e.g. the world frame. A "
                "point cloud without transforms to it stays in its sensor frame."
            )
        ),
    ] = None,
    camera_height: Annotated[
        int | None,
        Query(gt=0, description="Height of the camera images in pixels. Omit for full size."),
    ] = None,
) -> Response:
    """Returns the point clouds and camera frames of one tick, read with one MCAP read.

    The body holds one payload per channel. Each payload is prefixed with its channel
    id (u32), its kind (u8: 0 is an Arrow IPC point cloud, 1 is a JPEG camera frame),
    its log time in nanoseconds (u64) and its length in bytes (u64), little-endian.

    Raises:
        NotFoundError: If the sequence does not exist, does not belong to
            `dataset_id`, or has no tick at `seq_number`.
        HTTPException: 400 if a channel is missing from the recording or a message
            cannot be decoded.
    """
    try:
        payloads = get_tick_data_service.get_tick_data(
            session=session,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            seq_number=seq_number,
            target_frame_id=target_frame_id,
            camera_height=camera_height,
        )
    except McapAccessError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(exc)) from exc
    if payloads is None:
        raise NotFoundError(
            f"Tick {seq_number} not found in MCAP sequence {sequence_id} of dataset {dataset_id}."
        )
    return Response(
        content=tick_payload_encoding.encode_tick_payloads(payloads=payloads),
        media_type=tick_payload_encoding.MEDIA_TYPE,
        headers={"Cache-Control": "public, max-age=604800"},
    )
