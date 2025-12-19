"""Implementation of get all collections resolver function."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


# TODO(Michal, 06/2025): Use Paginated struct instead of offset and limit
def get_all(session: Session, offset: int = 0, limit: int = 100) -> list[CollectionTable]:
    """Retrieve all collections with pagination."""
    collections = session.exec(
        select(CollectionTable)
        .order_by(col(CollectionTable.created_at).asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(collections) if collections else []
