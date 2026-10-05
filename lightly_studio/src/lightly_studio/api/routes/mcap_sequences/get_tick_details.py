"""Route that returns the MCAP channel locators and annotations for one tick of a sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_ticks import TickDetailView
from lightly_studio.services import recording_service

get_tick_details_router = APIRouter()


@get_tick_details_router.get("/ticks/{seq_number}", response_model=TickDetailView)
def get_tick_details(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    seq_number: Annotated[int, Path(title="Tick position, zero-based", ge=0)],
    target_frame_id: Annotated[
        str | None,
        Query(
            description=(
                "The coordinate frame to express the 3D cuboids in, e.g. the frame the "
                "point clouds are shown in."
            )
        ),
    ] = None,
) -> TickDetailView:
    """Returns the tick details for one tick of a sequence.

    The tick is identified by `sequence_id` and `seq_number`. The response
    includes `recording_id` and, for each component, the fields
    needed to request a rendered frame from the recording's camera-frame endpoint:
    `channel_id` and `keyframe_log_time_ns`. It also includes the annotations
    attached to the tick, e.g. 3D cuboids.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The MCAP sequence the tick belongs to.
        seq_number: The zero-based position of the tick to fetch.
        target_frame_id: The coordinate frame to express the 3D cuboids in.

    Returns:
        The tick detail with per-channel locators and annotations.

    Raises:
        NotFoundError: If the sequence does not exist, does not belong to
            `dataset_id`, or has no tick at `seq_number`.
        HTTPException: 400 if the cuboids cannot be mapped to `target_frame_id`.
    """
    try:
        result = recording_service.get_tick_details(
            session=session,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            seq_number=seq_number,
            target_frame_id=target_frame_id,
        )
    except McapAccessError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise NotFoundError(
            f"Tick {seq_number} not found in MCAP sequence {sequence_id} of dataset {dataset_id}."
        )
    return result
