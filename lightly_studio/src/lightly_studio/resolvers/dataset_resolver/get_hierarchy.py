"""Implementation of get_child_collections resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import dataset_resolver


def get_hierarchy(session: Session, dataset_id: UUID) -> list[CollectionTable]:
    """Retrieve all collections of the given dataset.

    The collections are returned in the depth-first order, starting with the root collection.
    The relative order of children of any given node is the order in CollectionTable.children.
    """
    root_collection = dataset_resolver.get_root_collection(session=session, dataset_id=dataset_id)

    # Use a stack to perform depth-first traversal of the collection hierarchy.
    to_process = [root_collection]
    all_collections = []
    while to_process:
        current_collection = to_process.pop()
        all_collections.append(current_collection)
        to_process.extend(reversed(current_collection.children))

    return all_collections
