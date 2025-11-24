"""Implementation of get_all_by_dataset_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import FrameView, VideoFrameTable, VideoTable, VideoView


class VideosWithCount(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[VideoView]
    total_count: int
    next_cursor: int | None = None


def _convert_video_table_to_view(
    video: VideoTable, first_frame: VideoFrameTable | None
) -> VideoView:
    """Convert VideoTable to VideoView with only the first frame."""
    first_frame_view = None
    if first_frame:
        first_frame_view = FrameView(
            frame_number=first_frame.frame_number,
            frame_timestamp_s=first_frame.frame_timestamp_s,
            sample_id=first_frame.sample_id,
            sample=SampleView.model_validate(first_frame.sample),
        )

    return VideoView(
        width=video.width,
        height=video.height,
        duration_s=video.duration_s,
        fps=video.fps,
        file_name=video.file_name,
        file_path_abs=video.file_path_abs,
        sample_id=video.sample_id,
        sample=SampleView.model_validate(video.sample),
        frame=first_frame_view,
    )


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
    sample_ids: list[UUID] | None = None,
) -> VideosWithCount:
    """Retrieve samples for a specific dataset with optional filtering."""
    # Subquery to find the minimum frame_number for each video
    min_frame_subquery = (
        select(
            VideoFrameTable.parent_sample_id,
            func.min(col(VideoFrameTable.frame_number)).label("min_frame_number"),
        )
        .group_by(col(VideoFrameTable.parent_sample_id))
        .subquery()
    )

    # Query to get videos with their first frame (frame with min frame_number)
    # First join the subquery to VideoTable, then join VideoFrameTable
    samples_query = (
        select(VideoTable, VideoFrameTable)
        .join(VideoTable.sample)
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
        .where(SampleTable.dataset_id == dataset_id)
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

    total_count_query = (
        select(func.count())
        .select_from(VideoTable)
        .join(VideoTable.sample)
        .where(SampleTable.dataset_id == dataset_id)
    )

    if sample_ids:
        samples_query = samples_query.where(col(VideoTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(VideoTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(col(VideoTable.file_path_abs).asc())

    # Apply pagination if provided
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    # Fetch videos with their first frames and convert to VideoView
    results = session.exec(samples_query).all()
    video_views = [
        _convert_video_table_to_view(video, first_frame) for video, first_frame in results
    ]

    return VideosWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=next_cursor,
    )
