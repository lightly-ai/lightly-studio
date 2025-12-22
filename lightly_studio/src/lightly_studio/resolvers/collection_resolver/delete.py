"""Implementation of delete collection resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver


def delete(session: Session, collection_id: UUID) -> bool:
    """Delete a collection."""
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if not collection:
        return False

    session.delete(collection)
    session.commit()
    return True
