"""Implementation of get_all_by_dataset_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


class GetAllSamplesByDatasetIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[VideoFrameTable]
    total_count: int
    next_cursor: int | None = None


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByDatasetIdResult:
    """Retrieve samples for a specific dataset with optional filtering."""
    samples_query = (
        select(VideoFrameTable)
        .options(
            selectinload(VideoFrameTable.sample).options(
                joinedload(SampleTable.tags),
                # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            ),
        )
        .where(VideoFrameTable.sample.has(col(SampleTable.dataset_id) == dataset_id))
        .join(
            VideoTable,
            col(VideoFrameTable.video_sample_id) == col(VideoTable.sample_id),
        )
    )
    total_count_query = (
        select(func.count())
        .select_from(VideoFrameTable)
        .where(VideoFrameTable.sample.has(col(SampleTable.dataset_id) == dataset_id))
    )

    if sample_ids:
        samples_query = samples_query.where(col(VideoFrameTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(VideoFrameTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(
        col(VideoTable.file_path_abs).asc(), col(VideoFrameTable.frame_number).asc()
    )

    # Apply pagination if provided
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return GetAllSamplesByDatasetIdResult(
        samples=session.exec(samples_query).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
