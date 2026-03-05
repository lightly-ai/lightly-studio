"""Implementation of create collection resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, collection: CollectionCreate) -> CollectionTable:
    """Create a new collection in the database."""
    existing = collection_resolver.get_by_name(
        session=session,
        name=collection.name,
        parent_collection_id=collection.parent_collection_id,
    )
    if existing:
        raise ValueError(f"Collection with name '{collection.name}' already exists.")

    db_dataset: DatasetTable | None = None
    if collection.parent_collection_id is None:
        # If this is the root collection, create a dataset first.

        # The dataset doesn't have a physical foreign key to the collection,
        # but the collection has a physical foreign key to the dataset.
        db_dataset = DatasetTable()
        session.add(db_dataset)
        session.flush([db_dataset])
        dataset_id = db_dataset.dataset_id
    else:
        # Inherit dataset_id from parent collection.
        parent = collection_resolver.get_by_id(
            session=session, collection_id=collection.parent_collection_id
        )
        if parent is not None:
            dataset_id = parent.dataset_id
        else:
            raise ValueError(
                f"Parent collection with id {collection.parent_collection_id} not found."
            )

    # Create the table record, adding the determined dataset_id.
    db_collection = CollectionTable(
        **collection.model_dump(),
        dataset_id=dataset_id,
    )

    if db_dataset is not None:
        # Link the dataset back to its root collection.
        db_dataset.root_collection_id = db_collection.collection_id
        session.add(db_dataset)

    session.add(db_collection)
    session.commit()
    session.refresh(db_collection)

    return db_collection
