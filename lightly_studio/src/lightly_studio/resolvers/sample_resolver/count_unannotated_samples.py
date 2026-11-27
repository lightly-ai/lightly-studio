"""Implementation of count_unannotated_samples for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.unannotated_sample_count import UnannotatedSampleCount
from lightly_studio.resolvers.grid_filter_base import GridFilterBase


def count_unannotated_samples(
    session: Session,
    collection_id: UUID,
    grid_filter: GridFilterBase,
    unannotated_filter: GridFilterBase,
) -> UnannotatedSampleCount:
    """Count the unannotated samples in a collection, in total and for a filter.

    Args:
        session: The database session.
        collection_id: The ID of the collection to count samples in.
        grid_filter: The filter of the current count. Resolve its embedding region first.
        unannotated_filter: The filter that matches only the unannotated samples.

    Returns:
        The number of unannotated samples that match `grid_filter`, and the total number.
    """
    unannotated_ids = unannotated_filter.build_sample_ids_query(collection_id=collection_id)
    current_ids = grid_filter.build_sample_ids_query(collection_id=collection_id).where(
        col(SampleTable.sample_id).in_(unannotated_ids)
    )
    return UnannotatedSampleCount(
        current_count=_count(session=session, sample_ids=current_ids),
        total_count=_count(session=session, sample_ids=unannotated_ids),
    )


def _count(session: Session, sample_ids: SelectOfScalar[UUID]) -> int:
    return session.exec(select(func.count()).select_from(sample_ids.subquery())).one()
