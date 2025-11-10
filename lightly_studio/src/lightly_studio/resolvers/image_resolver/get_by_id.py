"""Implementation of get_by_id function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable


def get_by_id(session: Session, sample_id: UUID) -> ImageTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(ImageTable).where(ImageTable.sample_id == sample_id)).one_or_none()
