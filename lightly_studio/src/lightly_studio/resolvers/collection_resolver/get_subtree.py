"""Get a collection with its descendant collections."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_subtree(session: Session, collection_id: UUID) -> list[CollectionTable]:
    """Get the collection and all its descendant collections.

    Nothing bounds the depth: a caption is a sample of a child collection and can have
    captions of its own.

    Args:
        session: Database session.
        collection_id: ID of the root collection of the subtree.

    Returns:
        The collections, a parent before its children. Empty if the collection does not exist.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        return []
    subtree = [collection]
    for child in collection.children:
        subtree.extend(get_subtree(session=session, collection_id=child.collection_id))
    return subtree
