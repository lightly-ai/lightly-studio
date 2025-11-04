"""Resolvers for caption."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate, CaptionTable, CaptionViewsBySampleWithCount
from lightly_studio.models.sample import SampleTable


class GetAllCaptionsFromSampleResult(BaseModel):
    """Result wrapper for caption listings."""

    samples: Sequence[SampleTable]
    total_count: int
    next_cursor: int | None = None


def create_many(session: Session, captions: Sequence[CaptionCreate]) -> list[CaptionTable]:
    """Create many captions in bulk.

    Args:
        session: Database session
        captions: The captions to create

    Returns:
        The created captions
    """
    if not captions:
        return []

    db_captions = [CaptionTable.model_validate(caption) for caption in captions]
    session.bulk_save_objects(db_captions)
    session.commit()
    return db_captions


def get_all_captions_by_sample(
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
) -> CaptionViewsBySampleWithCount:
    """Get all samples with captions from the database.

    Args:
        session: Database session
        dataset_id: dataset_id parameter to filter the query
        pagination: Optional pagination parameters

    Returns:
        List of samples matching the filters, total number of samples with captions, next
        cursor (pagination)
    """
    """Selects distinct samples with captions, and orders by creation time and caption ID."""
    query = (
        select(SampleTable)
        .join(CaptionTable)
        .where(SampleTable.dataset_id == dataset_id)
        .order_by(
            col(CaptionTable.created_at).asc(),
            col(CaptionTable.caption_id).asc(),
        )
        .distinct()
    )

    """Selects distinct samples with captions for counting total number."""
    count_subquery = (
        select(SampleTable.sample_id)
        .join(CaptionTable)
        .where(SampleTable.dataset_id == dataset_id)
        .distinct()
        .subquery()
    )

    if pagination is not None:
        query = query.offset(pagination.offset).limit(pagination.limit)

    samples = session.exec(query).all()

    count_query = select(func.count()).select_from(count_subquery)
    total_count = session.exec(count_query).one()

    next_cursor: int | None = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return CaptionViewsBySampleWithCount(
        samples=samples,
        total_count=total_count,
        next_cursor=next_cursor,
    )
