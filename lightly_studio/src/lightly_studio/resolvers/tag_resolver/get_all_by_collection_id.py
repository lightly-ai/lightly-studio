"""Implementation of get_all_by_collection_id function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.tag import TagTable


# TODO(Michal, 06/2025): Use Paginated struct instead of offset/limit.
def get_all_by_collection_id(
    session: Session, collection_id: UUID, offset: int = 0, limit: int | None = None
) -> list[TagTable]:
    """Retrieve all tags with pagination."""
    query = (
        select(TagTable)
        .where(TagTable.collection_id == collection_id)
        .order_by(col(TagTable.created_at).asc(), col(TagTable.tag_id).asc())
        .offset(offset)
    )
    if limit is not None:
        query = query.limit(limit)
    tags = session.exec(query).all()
    return list(tags) if tags else []
