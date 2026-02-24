"""Implementation of get_sample_ids function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None,
) -> set[UUID]:
    """Get sample IDs for a given collection.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        filters: The image filters to apply.

    Returns:
        List of sample ids matching the given filters.

    """
    query = (
        select(ImageTable.sample_id)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    if filters:
        query = filters.apply(query)
    sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)
