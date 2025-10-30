"""Implementation of update function for images."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.resolvers import image_resolver


def update(session: Session, sample_id: UUID, sample_data: ImageCreate) -> ImageTable | None:
    """Update an existing sample."""
    sample = image_resolver.get_by_id(
        session=session, dataset_id=sample_data.dataset_id, sample_id=sample_id
    )
    if not sample:
        return None

    sample.file_name = sample_data.file_name
    sample.width = sample_data.width
    sample.height = sample_data.height
    sample.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(sample)
    return sample
