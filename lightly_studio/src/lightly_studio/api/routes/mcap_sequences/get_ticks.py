"""Route that returns the ordered list of ticks for an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_ticks import TickListView
from lightly_studio.services import recording_service

get_ticks_router = APIRouter()


@get_ticks_router.get("/ticks", response_model=TickListView)
def get_ticks(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
) -> TickListView:
    """Returns the ordered list of ticks for an MCAP sequence.

    Each tick holds its position (`seq_number`) and the anchor log time
    (`timestamp_ns`) that was recorded at index time. The list is ordered by
    `seq_number` ascending.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The MCAP sequence to list ticks for.

    Returns:
        The tick list.

    Raises:
        NotFoundError: If the sequence does not exist or does not belong to
            `dataset_id`.
    """
    result = recording_service.get_ticks(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id
    )
    if result is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return result
