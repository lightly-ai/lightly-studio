"""Implementation of count_by_collection_id for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, func, select

from lightly_studio.models.sample import SampleTable


def count_by_collection_id(session: Session, collection_id: UUID) -> int:
    """Count the number of samples in a collection."""
    return session.exec(
        select(func.count())
        .select_from(SampleTable)
        .where(SampleTable.collection_id == collection_id)
    ).one()
