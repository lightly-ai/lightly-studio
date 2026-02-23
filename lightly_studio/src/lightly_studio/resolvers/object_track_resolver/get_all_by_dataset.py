"""Get all object tracks for a dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def get_all_by_dataset(
    session: Session,
    dataset_id: UUID,
) -> Sequence[ObjectTrackTable]:
    """Retrieve all tracks belonging to a given dataset.

    Args:
        session: Database session for executing the operation.
        dataset_id: UUID of the root collection to retrieve tracks for.

    Returns:
        All ObjectTrackTable instances for the dataset, ordered by object_track_number.
    """
    return session.exec(
        select(ObjectTrackTable)
        .where(col(ObjectTrackTable.dataset_id) == dataset_id)
        .order_by(col(ObjectTrackTable.object_track_number).asc())
    ).all()
