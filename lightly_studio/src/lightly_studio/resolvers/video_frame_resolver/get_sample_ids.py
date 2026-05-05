"""Implementation of get_sample_ids function for video frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: VideoFrameFilter | None = None,
) -> set[UUID]:
    """Get sample IDs for a given collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to scope results to.
        filters: The video frame filters to apply.

    Returns:
        Set of sample ids matching the given filters.
    """
    query = (
        select(VideoFrameTable.sample_id).join(VideoFrameTable.sample).join(VideoFrameTable.video)
    )
    query = query.where(col(SampleTable.collection_id) == collection_id)
    if filters is not None:
        query = filters.apply(query)
    sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)
