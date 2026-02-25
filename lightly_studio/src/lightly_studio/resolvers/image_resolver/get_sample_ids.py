"""Implementation of get_sample_ids function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers.image_filter import ImageFilter


def get_sample_ids(
    session: Session,
    filters: ImageFilter,
) -> set[UUID]:
    """Get sample IDs for a given collection.

    Args:
        session: The database session.
        filters: The image filters to apply.

    Returns:
        List of sample ids matching the given filters.

    Raises:
        ValueError: If collection ID is not provided in the sample filter.
    """
    if not filters.sample_filter or not filters.sample_filter.collection_id:
        raise ValueError("Collection ID must be provided in the sample filter.")
    query = (
        select(ImageTable.sample_id)
        .join(ImageTable.sample)
    )
    query = filters.apply(query)
    sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)
