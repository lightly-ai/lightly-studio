"""Implementation of get_by_id function for images."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable


def get_by_id(
    session: Session, sample_id: UUID, load_option: LoaderOption | None = None
) -> ImageTable | None:
    """Retrieve a single sample by ID."""
    query = select(ImageTable).where(ImageTable.sample_id == sample_id)
    if load_option is not None:
        query = query.options(load_option)
    return session.exec(query).unique().one_or_none()
