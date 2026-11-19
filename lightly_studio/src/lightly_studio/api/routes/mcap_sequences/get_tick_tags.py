"""Route that returns the tags on the ticks of an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_ticks import TickTagListView
from lightly_studio.services import recording_service

get_tick_tags_router = APIRouter()


@get_tick_tags_router.get("/tick-tags", response_model=TickTagListView)
def get_tick_tags(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
) -> TickTagListView:
    """Returns the tags on the ticks of an MCAP sequence, grouped by tag.

    Each entry holds a tag and the positions (`seq_number`) of the ticks that carry it,
    in ascending order. Only tags on at least one tick are listed, ordered by name.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The MCAP sequence to list tick tags for.

    Returns:
        The tags with their tick positions.

    Raises:
        NotFoundError: If the sequence does not exist or does not belong to
            `dataset_id`.
    """
    result = recording_service.get_tick_tags(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id
    )
    if result is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return result
