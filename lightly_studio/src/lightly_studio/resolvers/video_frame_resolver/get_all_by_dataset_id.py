"""Implementation of get_all_by_collection_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter


class VideoFramesWithCount(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[VideoFrameTable]
    total_count: int
    next_cursor: int | None = None


def get_all_by_collection_id(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    video_frame_filter: VideoFrameFilter | None = None,
) -> VideoFramesWithCount:
    """Retrieve video frame samples for a specific collection with optional filtering."""
    filters: list[Any] = [SampleTable.collection_id == collection_id]

    base_query = (
        select(VideoFrameTable)
        .join(VideoFrameTable.sample)
        .join(VideoFrameTable.video)
        .where(*filters)
    )

    if video_frame_filter:
        base_query = video_frame_filter.apply(base_query)

    samples_query = base_query.order_by(
        col(VideoTable.file_path_abs).asc(), col(VideoFrameTable.frame_number).asc()
    )

    # Apply pagination if provided
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count_query = select(func.count()).select_from(base_query.subquery())
    total_count = session.exec(total_count_query).one()
    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return VideoFramesWithCount(
        samples=session.exec(samples_query).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
