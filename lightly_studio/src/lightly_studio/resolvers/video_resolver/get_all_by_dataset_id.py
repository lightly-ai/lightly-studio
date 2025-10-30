"""Implementation of get_all_by_dataset_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.samples_filter import SampleFilter


class GetAllSamplesByDatasetIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[VideoTable]
    total_count: int
    next_cursor: int | None = None


def get_all_by_dataset_id(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
    filters: SampleFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByDatasetIdResult:
    """Retrieve samples for a specific dataset with optional filtering."""
    samples_query = (
        select(VideoTable)
        .options(
            selectinload(VideoTable.sample).options(
                joinedload(SampleTable.tags),
                # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            ),
        )
        .where(VideoTable.dataset_id == dataset_id)
    )
    total_count_query = (
        select(func.count()).select_from(VideoTable).where(VideoTable.dataset_id == dataset_id)
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
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

    return GetAllSamplesByDatasetIdResult(
        samples=session.exec(samples_query).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
