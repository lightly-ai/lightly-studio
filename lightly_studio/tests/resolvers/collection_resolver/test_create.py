from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import collection_resolver


def test_create(db_session: Session) -> None:
    ds = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="my_collection", sample_type=SampleType.IMAGE),
    )
    assert ds.name == "my_collection"
    assert ds.dataset_id is not None

    # Check that the dataset record was created and links to the root collection
    db_dataset = db_session.get(DatasetTable, ds.dataset_id)
    assert db_dataset is not None

    # Creating a collection with the same name should raise an error.
    with pytest.raises(ValueError, match=r"Collection with name 'my_collection' already exists."):
        collection_resolver.create(
            session=db_session,
            collection=CollectionCreate(name="my_collection", sample_type=SampleType.IMAGE),
        )


def test_create__collections_with_same_name_different_parents(db_session: Session) -> None:
    # Create two root collections
    root1 = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="root1", sample_type=SampleType.IMAGE),
    )
    root2 = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="root2", sample_type=SampleType.IMAGE),
    )

    # Create child collections with the same name under different parents
    child1 = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="shared_name",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=root1.collection_id,
        ),
    )
    child2 = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="shared_name",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=root2.collection_id,
        ),
    )

    assert child1.name == "shared_name"
    assert child2.name == "shared_name"
    assert child1.collection_id != child2.collection_id
    assert child1.parent_collection_id == root1.collection_id
    assert child2.parent_collection_id == root2.collection_id


def test_create__collections_with_same_name_same_parent_fails(db_session: Session) -> None:
    # Create a root collection
    root = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
    )

    # Create a child collection
    collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="child",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=root.collection_id,
        ),
    )

    # Creating another child with the same name under the same parent should fail
    with pytest.raises(ValueError, match=r"Collection with name 'child' already exists."):
        collection_resolver.create(
            session=db_session,
            collection=CollectionCreate(
                name="child",
                sample_type=SampleType.ANNOTATION,
                parent_collection_id=root.collection_id,
            ),
        )


def test_create__root_collections_with_same_name_fails(db_session: Session) -> None:
    # Create a root collection
    collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
    )

    # Creating another root collection with the same name should fail
    with pytest.raises(ValueError, match=r"Collection with name 'root' already exists."):
        collection_resolver.create(
            session=db_session,
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
        )


def test_create__with_existing_dataset_id(db_session: Session) -> None:
    # Pre-create a dataset
    dataset_id = uuid.uuid4()
    db_dataset = DatasetTable(dataset_id=dataset_id)
    db_session.add(db_dataset)
    db_session.commit()

    # `create()` should not take dataset_id, it should create one or inherit it.
    collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="new_root",
            sample_type=SampleType.IMAGE,
        ),
    )

    assert collection.dataset_id != dataset_id
    assert collection.dataset_id is not None
