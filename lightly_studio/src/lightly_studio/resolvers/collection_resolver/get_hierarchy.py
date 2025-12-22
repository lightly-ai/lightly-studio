"""Implementation of get_child_collections resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_hierarchy(session: Session, dataset_id: UUID) -> list[CollectionTable]:
    """Retrieve all child collections of the given root collection, including the root itself.

    The collections are returned in the depth-first order, starting with the root collection.
    The relative order of children of any given node is the order in CollectionTable.children.
    """
    root_collection = collection_resolver.get_by_id(session=session, collection_id=dataset_id)
    if root_collection is None:
        raise ValueError(f"Collection with id {dataset_id} not found.")

    # Use a stack to perform depth-first traversal of the collection hierarchy.
    to_process = [root_collection]
    all_collections = []
    while to_process:
        current_collection = to_process.pop()
        all_collections.append(current_collection)
        to_process.extend(reversed(current_collection.children))

    return all_collections
