"""Implementation of get_filtered_samples resolver function."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class SamplesWithCount(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[SampleTable]
    total_count: int
    # Number of captions of the matching samples. A sample can have several captions.
    total_caption_count: int
    next_cursor: int | None = None


def get_filtered_samples(
    session: Session,
    collection_id: UUID,
    filters: SampleFilter | None = None,
    pagination: Paginated | None = None,
) -> SamplesWithCount:
    """Retrieve samples for a specific collection with optional filtering."""
    collection = session.get(CollectionTable, collection_id)
    sample_type = collection.sample_type if collection is not None else None
    samples_query = select(SampleTable).where(col(SampleTable.collection_id) == collection_id)
    total_count_query = (
        select(func.count())
        .select_from(SampleTable)
        .where(col(SampleTable.collection_id) == collection_id)
    )

    if filters is not None:
        samples_query = _apply_sample_filter(
            filters=filters, query=samples_query, sample_type=sample_type
        )
        total_count_query = _apply_sample_filter(
            filters=filters, query=total_count_query, sample_type=sample_type
        )

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
        total_caption_count=_count_captions(
            session=session, collection_id=collection_id, filters=filters, sample_type=sample_type
        ),
        next_cursor=next_cursor,
    )


def _count_captions(
    session: Session,
    collection_id: UUID,
    filters: SampleFilter | None,
    sample_type: SampleType | None,
) -> int:
    """Count the captions of the samples in a collection that match the filters."""
    captions_query = (
        select(func.count())
        .select_from(SampleTable)
        .join(CaptionTable, col(CaptionTable.parent_sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if filters is not None:
        captions_query = _apply_sample_filter(
            filters=filters, query=captions_query, sample_type=sample_type
        )
    return session.exec(captions_query).one()


def _apply_sample_filter(
    query: QueryType, filters: SampleFilter, sample_type: SampleType | None
) -> QueryType:
    if filters.query_expr is not None:
        query = query.outerjoin(VideoTable, col(VideoTable.sample_id) == col(SampleTable.sample_id))
    return filters.apply(query=query, sample_type=sample_type)
