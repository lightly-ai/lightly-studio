"""Get collection_id by group sample_id."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import GroupTable
from lightly_studio.models.sample import SampleTable


def get_collection_id_by_group_id(session: Session, group_id: UUID) -> UUID | None:
    """Retrieve collection_id for a group by its group_id.

    Args:
        session: Database session for executing queries.
        group_id: The group_id of the group.

    Returns:
        The collection_id of the group, or None if the group doesn't exist.
    """
    query = (
        select(SampleTable.collection_id)
        .join(GroupTable, col(GroupTable.sample_id) == col(SampleTable.sample_id))
        .where(col(GroupTable.sample_id) == group_id)
    )
    return session.exec(query).one_or_none()
