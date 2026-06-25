"""Implementation of get_sample_ids function for video frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

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
    return (filters or VideoFrameFilter()).build_sample_ids_query(collection_id=collection_id)


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
