"""Get all object tracks for a dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> Sequence[ObjectTrackTable]:
    """Retrieve all object tracks for a given dataset."""
    stmt = select(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id)
    return session.exec(stmt).all()
