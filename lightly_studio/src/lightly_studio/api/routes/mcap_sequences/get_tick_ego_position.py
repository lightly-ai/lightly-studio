"""Route that returns the ego position for one tick of a sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_ticks import EgoPositionFrames, TickEgoPositionView
from lightly_studio.services import recording_service

get_tick_ego_position_router = APIRouter()


@get_tick_ego_position_router.get(
    "/ticks/{seq_number}/ego-position", response_model=TickEgoPositionView
)
def get_tick_ego_position(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    seq_number: Annotated[int, Path(title="Tick position, zero-based", ge=0)],
    frames: Annotated[EgoPositionFrames, Query()],
) -> TickEgoPositionView:
    """Returns the position of the ego for one tick of a sequence.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The MCAP sequence the tick belongs to.
        seq_number: The zero-based position of the tick.
        frames: The frame the scene is shown in and the frame attached to the ego.

    Returns:
        The origin of the ego frame in the target frame at the tick timestamp. The
        position is `None` if no transform connects the frames.

    Raises:
        NotFoundError: If the sequence does not exist, does not belong to `dataset_id`,
            or has no tick at `seq_number`.
    """
    result = recording_service.get_tick_ego_position(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        seq_number=seq_number,
        frames=frames,
    )
    if result is None:
        raise NotFoundError(
            f"Tick {seq_number} not found in MCAP sequence {sequence_id} of dataset {dataset_id}."
        )
    return result
