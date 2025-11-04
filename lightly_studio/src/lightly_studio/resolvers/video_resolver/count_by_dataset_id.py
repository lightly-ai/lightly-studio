"""Implementation of count_by_dataset_id function for videos."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable


def count_by_dataset_id(session: Session, dataset_id: UUID) -> int:
    """Count the number of samples in a dataset."""
    return session.exec(
        select(func.count())
        .select_from(VideoTable)
        .join(SampleTable, col(VideoTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.dataset_id == dataset_id)
    ).one()
