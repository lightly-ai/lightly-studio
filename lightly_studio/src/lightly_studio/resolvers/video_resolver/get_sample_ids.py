"""Implementation of get_sample_ids function for videos."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: VideoFilter | None,
) -> set[UUID]:
    """Get sample IDs for a given collection.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        filters: The video filters to apply.

    Returns:
        List of sample ids matching the given filters.

    """
    query = (
        select(VideoTable.sample_id)
        .join(VideoTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    if filters:
        query = filters.apply(query)
    sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)
