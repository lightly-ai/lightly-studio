"""Implementation of create dataset resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import collection_resolver


def create_dataset(session: Session, collection: CollectionCreate) -> CollectionTable:
    """Create a new dataset.

    This function creates a new root collection and a corresponding entry in the
    DatasetTable. It also ensures the collection's dataset_id is set to its own
    collection_id.

    Args:
        session: The database session.
        collection: The collection creation parameters.

    Returns:
        The created collection.
    """
    db_collection = collection_resolver.create(
        session=session,
        collection=collection,
    )

    # Create a corresponding dataset for the collection.
    dataset = DatasetTable(
        dataset_id=db_collection.collection_id,
        root_collection_id=db_collection.collection_id,
    )
    session.add(dataset)

    # Update the collection with its own ID as dataset_id.
    db_collection.dataset_id = db_collection.collection_id
    session.add(db_collection)

    session.commit()
    session.refresh(db_collection)

    return db_collection
