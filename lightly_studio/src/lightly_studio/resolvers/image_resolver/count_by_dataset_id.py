"""Implementation of count_by_dataset_id function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, func, select

from lightly_studio.models.image import ImageTable


def count_by_dataset_id(session: Session, dataset_id: UUID) -> int:
    """Count the number of samples in a dataset."""
    return session.exec(
        select(func.count()).select_from(ImageTable).where(ImageTable.dataset_id == dataset_id)
    ).one()
