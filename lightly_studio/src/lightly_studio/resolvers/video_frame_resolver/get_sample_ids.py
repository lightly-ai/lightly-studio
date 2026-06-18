"""Implementation of get_sample_ids function for video frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter


def build_sample_ids_query(
    collection_id: UUID,
    filters: VideoFrameFilter | None = None,
) -> SelectOfScalar[UUID]:
    """Build the query selecting distinct sample ids for a given collection.

    Args:
        collection_id: The ID of the collection to scope results to.
        filters: The video frame filters to apply.

    Returns:
        A query selecting the distinct sample ids matching the given filters.
    """
    query = (
        select(VideoFrameTable.sample_id).join(VideoFrameTable.sample).join(VideoFrameTable.video)
    )
    query = query.where(col(SampleTable.collection_id) == collection_id)
    if filters is not None:
        query = filters.apply(query)
    return query.distinct()


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
    query = build_sample_ids_query(collection_id=collection_id, filters=filters)
    return set(session.exec(query).all())
