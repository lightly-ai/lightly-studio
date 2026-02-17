"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.group import SampleGroupLinkTable


def get_group_sample_counts(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, int]:
    """Get the count of samples for each group.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to count samples for.

    Returns:
        Dictionary mapping group sample_id to the count of samples in that group.
    """
    if not group_sample_ids:
        return {}

    # Count samples for each group
    count_query = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            func.count(col(SampleGroupLinkTable.sample_id)).label("sample_count"),
        )
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .group_by(col(SampleGroupLinkTable.parent_sample_id))
    )

    results = session.exec(count_query).all()

    return dict(results)
