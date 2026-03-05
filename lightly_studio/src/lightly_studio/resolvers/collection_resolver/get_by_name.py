"""Implementation of get collection by name resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


def get_by_name(
    session: Session,
    name: str,
    parent_collection_id: UUID | None = None,
) -> CollectionTable | None:
    """Retrieve a single collection by name and optionally its parent or root status.

    Args:
        session: Database session.
        name: Name of the collection to retrieve.
        parent_collection_id: Optional UUID of the parent collection. If None,
            searches for a root collection.

    Returns:
        The collection if found, otherwise None.
    """
    statement = select(CollectionTable).where(CollectionTable.name == name)
    if parent_collection_id is not None:
        statement = statement.where(
            col(CollectionTable.parent_collection_id) == parent_collection_id
        )
    else:
        statement = statement.where(col(CollectionTable.parent_collection_id).is_(None))

    return session.exec(statement).one_or_none()
