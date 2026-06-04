"""Implementation of the create collection resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, collection: CollectionCreate) -> CollectionTable:
    """Creates a new collection in the database.

    If the collection has no parent (root collection), a new dataset is also created
    and linked to the collection. Otherwise, the collection inherits the dataset ID
    from its parent.

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
        if collection.parent_collection_id is None:
            raise ValueError(
                f"A dataset named '{collection.name}' already exists. Dataset names must "
                f"be unique. To open it instead of creating a new one, use "
                f"`load(name='{collection.name}')` or `load_or_create(name='{collection.name}')`. "
                f"To create a separate dataset, choose a different name."
            )
        raise ValueError(
            f"A collection named '{collection.name}' already exists under the same parent "
            f"collection. Collection names must be unique within their parent. Choose a "
            f"different name."
        )

    db_dataset: DatasetTable | None = None
    if collection.parent_collection_id is None:
        # If this is the root collection, create a dataset first.
        db_dataset = DatasetTable()
        session.add(db_dataset)
        session.flush([db_dataset])
        dataset_id = db_dataset.dataset_id
    else:
        # Inherit dataset_id from parent collection.
        parent = collection_resolver.get_by_id(
            session=session, collection_id=collection.parent_collection_id
        )
        if parent is None:
            raise ValueError(f"Parent collection {collection.parent_collection_id} not found")
        dataset_id = parent.dataset_id

    db_collection = CollectionTable(
        **collection.model_dump(),
        dataset_id=dataset_id,
    )

    if db_dataset is not None:
        session.add(db_dataset)

    session.add(db_collection)
    session.commit()
    session.refresh(db_collection)
    return db_collection
