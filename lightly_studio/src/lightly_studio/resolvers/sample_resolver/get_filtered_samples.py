"""Implementation of get_filtered_samples resolver function."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


class SamplesWithCount(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[SampleTable]
    total_count: int
    next_cursor: int | None = None


def get_filtered_samples(
    session: Session,
    filters: SampleFilter | None = None,
    pagination: Paginated | None = None,
) -> SamplesWithCount:
    """Retrieve samples for a specific collection with optional filtering."""
    samples_query = select(SampleTable)
    total_count_query = select(func.count()).select_from(SampleTable)

    if filters is not None:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # Apply default ordering
    samples_query = samples_query.order_by(
        col(SampleTable.created_at).asc(),
        col(SampleTable.sample_id).asc(),
    )

    # Apply pagination if provided
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()

    next_cursor = None
    if pagination is not None and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return SamplesWithCount(
        samples=session.exec(samples_query).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
