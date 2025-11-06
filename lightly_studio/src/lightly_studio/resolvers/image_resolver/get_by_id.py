"""Implementation of get_by_id function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable


# TODO MICHAL
def get_by_id(session: Session, dataset_id: UUID, sample_id: UUID) -> ImageTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(
        select(ImageTable).where(
            ImageTable.sample_id == sample_id, ImageTable.dataset_id == dataset_id
        )
    ).one_or_none()
