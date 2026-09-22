"""Route that returns the MCAP channel locators for one tick of a sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_ticks import TickDetailView
from lightly_studio.services import recording_service

get_tick_router = APIRouter()


@get_tick_router.get("/ticks/{seq_number}", response_model=TickDetailView)
def get_tick(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    seq_number: Annotated[int, Path(title="Tick position, zero-based", ge=0)],
) -> TickDetailView:
    """Returns the tick details for one tick of a sequence.

    The tick is identified by `sequence_id` and `seq_number`. The response
    includes `recording_id` and, for each component, the fields
    needed to request a rendered frame from the recording's camera-frame endpoint:
    `channel_id` and `keyframe_log_time_ns`.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The MCAP sequence the tick belongs to.
        seq_number: The zero-based position of the tick to fetch.

    Returns:
        The tick detail with per-channel locators.

    Raises:
        NotFoundError: If the sequence does not exist, does not belong to
            `dataset_id`, or has no tick at `seq_number`.
    """
    result = recording_service.get_tick_details(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        seq_number=seq_number,
    )
    if result is None:
        raise NotFoundError(
            f"Tick {seq_number} not found in MCAP sequence {sequence_id} of dataset {dataset_id}."
        )
    return result
