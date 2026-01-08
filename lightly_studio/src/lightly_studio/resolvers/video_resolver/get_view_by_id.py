"""Find a video view by its id."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable, VideoView
from lightly_studio.resolvers.video_resolver.get_all_by_collection_id import (
    convert_video_table_to_view,
)


def get_view_by_id(session: Session, sample_id: UUID) -> VideoView | None:
    """Retrieve a video view by its ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A VideoView object or none.
    """
    min_frame_subquery = (
        select(
            VideoFrameTable.parent_sample_id,
            func.min(VideoFrameTable.frame_number).label("min_frame_number"),
        )
        .group_by(col(VideoFrameTable.parent_sample_id))
        .subquery()
    )

    query = (
        select(VideoTable, VideoFrameTable)
        .outerjoin(
            min_frame_subquery,
            min_frame_subquery.c.parent_sample_id == VideoTable.sample_id,
        )
        .outerjoin(
            VideoFrameTable,
            and_(
                col(VideoFrameTable.parent_sample_id) == col(VideoTable.sample_id),
                col(VideoFrameTable.frame_number) == min_frame_subquery.c.min_frame_number,
            ),
        )
        .where(VideoTable.sample_id == sample_id)
        .options(
            selectinload(VideoFrameTable.sample).options(
                joinedload(SampleTable.tags),
                # Ignore type checker error - false positive from TYPE_CHECKING.
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            ),
            selectinload(VideoTable.sample).options(
                joinedload(SampleTable.tags),
                # Ignore type checker error - false positive from TYPE_CHECKING.
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            ),
        )
    )

    video, first_frame = session.exec(query).one()
    return convert_video_table_to_view(video, first_frame)
