"""Implementation of the create collection resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, collection: CollectionCreate) -> CollectionTable:
    """Creates a new collection in the database.

    Args:
        session: The database session to use.
        collection: The data for the new collection.

    Returns:
        The created collection.

    Raises:
        ValueError:
            If a collection with the same name already exists under the same parent.
    """
    existing = collection_resolver.get_by_name(
        session=session,
        name=collection.name,
        parent_collection_id=collection.parent_collection_id,
    )
    if existing:
        raise ValueError(f"Collection with name '{collection.name}' already exists.")
    db_collection = CollectionTable.model_validate(collection)
    session.add(db_collection)
    session.commit()
    session.refresh(db_collection)
    return db_collection
