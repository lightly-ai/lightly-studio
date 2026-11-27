"""Get the sample IDs of the images of a collection in the default order of a dataset query."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def get_ordered_sample_ids(
    session: Session, collection_id: UUID, filters: ImageFilter | None
) -> list[UUID]:
    """Get the sample IDs of the images that match a filter, by creation time and sample ID.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        filters: The image filters. The embedding region of the filters is ignored.

    Returns:
        List of sample ids matching the given filters, by creation time and sample ID.
    """
    matching_ids = image_resolver.build_sample_ids_query(
        collection_id=collection_id, filters=filters
    )
    query = (
        select(ImageTable.sample_id)
        .where(col(ImageTable.sample_id).in_(matching_ids))
        .order_by(col(ImageTable.created_at), col(ImageTable.sample_id))
    )
    return list(session.exec(query).all())
