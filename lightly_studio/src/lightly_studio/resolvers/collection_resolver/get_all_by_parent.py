"""Implementation of the get collections by parent resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import joinedload
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


def get_all_by_parent(
    session: Session, parent_collection_id: UUID | None, name: str | None
) -> list[CollectionTable]:
    """Get the child collections of a parent, sorted by creation time.

    Args:
        session: The database session.
        parent_collection_id: The ID of the parent. None gets the root collections.
        name: The name of the collections to get. None gets all names.
    """
    statement = (
        select(CollectionTable)
        .where(col(CollectionTable.parent_collection_id) == parent_collection_id)
        .options(joinedload(CollectionTable.group_component_definition))  # type: ignore[arg-type]
    )
    if name is not None:
        statement = statement.where(CollectionTable.name == name)
    return list(session.exec(statement.order_by(col(CollectionTable.created_at))).all())
