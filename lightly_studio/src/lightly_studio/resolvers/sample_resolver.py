"""Handler for database operations related to samples."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ScalarResult
from sqlmodel import Session, col, func, insert, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.sample import SampleCreate, SamplesWithCount, SampleTable


def create(session: Session, sample: SampleCreate) -> SampleTable:
    """Create a new sample in the database."""
    db_sample = SampleTable.model_validate(sample)
    session.add(db_sample)
    session.commit()
    session.refresh(db_sample)
    return db_sample


def create_many(session: Session, samples: Sequence[SampleCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit."""
    # Note: We are using bulk insert for SampleTable to get sample_ids efficiently.
    statement = (
        insert(SampleTable)
        .values([sample.model_dump() for sample in samples])
        .returning(col(SampleTable.sample_id))
    )
    sample_ids: ScalarResult[UUID] = session.execute(statement).scalars()
    return list(sample_ids)


def get_by_id(session: Session, sample_id: UUID) -> SampleTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(SampleTable).where(SampleTable.sample_id == sample_id)).one_or_none()


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[SampleTable]:
    """Retrieve multiple samples by their IDs.

    Output order matches the input order.
    """
    results = session.exec(
        select(SampleTable).where(col(SampleTable.sample_id).in_(sample_ids))
    ).all()
    # Return samples in the same order as the input IDs
    sample_map = {sample.sample_id: sample for sample in results}
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]


def get_all_samples_with_captions(
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
) -> SamplesWithCount:
    """Get all samples with captions from the database.

    Args:
        session: Database session
        dataset_id: dataset_id parameter to filter the query
        pagination: Optional pagination parameters

    Returns:
        List of samples matching the filters, total number of samples with captions, next
        cursor (pagination)
    """
    # Selects distinct samples with captions, and orders by creation time and caption ID.
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

    # Selects distinct samples with captions for counting total number.
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

    return SamplesWithCount(
        samples=samples,
        total_count=total_count,
        next_cursor=next_cursor,
    )
