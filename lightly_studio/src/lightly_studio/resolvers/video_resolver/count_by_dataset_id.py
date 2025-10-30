"""Implementation of count_by_dataset_id function for videos."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.models.video import VideoTable
from sqlmodel import Session, func, select


def count_by_dataset_id(session: Session, dataset_id: UUID) -> int:
    """Count the number of samples in a dataset."""
    return session.exec(
        select(func.count()).select_from(VideoTable).where(VideoTable.dataset_id == dataset_id)
    ).one()
