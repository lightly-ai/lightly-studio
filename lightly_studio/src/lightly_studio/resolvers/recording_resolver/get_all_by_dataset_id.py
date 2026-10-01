"""Get all recordings for a dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.recording import RecordingTable


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> Sequence[RecordingTable]:
    """Retrieve all recordings for a given dataset."""
    stmt = select(RecordingTable).where(col(RecordingTable.dataset_id) == dataset_id)
    return session.exec(stmt).all()
