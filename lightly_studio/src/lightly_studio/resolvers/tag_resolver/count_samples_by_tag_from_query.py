"""Implementation of count_samples_by_tag_from_query function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTagLinkTable


def count_samples_by_tag_from_query(
    session: Session,
    sample_ids_query: SelectOfScalar[UUID],
) -> dict[UUID, int]:
    """Count, for each tag, how many samples matched by ``sample_ids_query`` carry it.

    Args:
        session: The database session.
        sample_ids_query: Query that selects a single ``sample_id`` column.

    Returns:
        Mapping from tag ID to the number of matched samples with that tag. Tags that
        no matched sample carries are not in the mapping.
    """
    sample_ids_subquery = sample_ids_query.subquery()
    query = (
        select(SampleTagLinkTable.tag_id, func.count())
        .where(col(SampleTagLinkTable.sample_id).in_(select(sample_ids_subquery.c[0])))
        .group_by(col(SampleTagLinkTable.tag_id))
    )
    return {tag_id: count for tag_id, count in session.exec(query).all() if tag_id is not None}
