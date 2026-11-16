"""Get the IDs of a collection and of its descendant collections."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_subtree_ids(session: Session, collection_id: UUID) -> list[UUID]:
    """Get the ID of the collection and the IDs of all its descendant collections.

    Nothing bounds the depth: a caption is a sample of a child collection and can have
    captions of its own.

    Args:
        session: Database session.
        collection_id: ID of the root collection of the subtree.

    Returns:
        The IDs, a collection before its children. Empty if the collection does not exist.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        return []
    subtree_ids = [collection_id]
    parent_ids = [collection_id]
    while parent_ids:
        child_ids = list(
            session.exec(
                select(CollectionTable.collection_id).where(
                    col(CollectionTable.parent_collection_id).in_(parent_ids)
                )
            ).all()
        )
        subtree_ids.extend(child_ids)
        parent_ids = child_ids
    return subtree_ids
