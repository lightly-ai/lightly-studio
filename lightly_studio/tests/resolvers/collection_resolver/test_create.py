from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_create(test_db: Session) -> None:
    ds = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="my_collection", sample_type=SampleType.IMAGE),
    )
    assert ds.name == "my_collection"

    # Creating a collection with the same name should raise an error.
    with pytest.raises(ValueError, match="Collection with name 'my_collection' already exists."):
        collection_resolver.create(
            session=test_db,
            collection=CollectionCreate(name="my_collection", sample_type=SampleType.IMAGE),
        )


def test_create__collections_with_same_name_different_parents(test_db: Session) -> None:
    # Create two root collections
    root1 = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="root1", sample_type=SampleType.IMAGE),
    )
    root2 = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="root2", sample_type=SampleType.IMAGE),
    )

    # Create child collections with the same name under different parents
    child1 = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(
            name="shared_name",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=root1.collection_id,
        ),
    )
    child2 = collection_resolver.create(
        session=test_db,
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


def test_create__collections_with_same_name_same_parent_fails(test_db: Session) -> None:
    # Create a root collection
    root = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
    )

    # Create a child collection
    collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(
            name="child",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=root.collection_id,
        ),
    )

    # Creating another child with the same name under the same parent should fail
    with pytest.raises(ValueError, match="Collection with name 'child' already exists."):
        collection_resolver.create(
            session=test_db,
            collection=CollectionCreate(
                name="child",
                sample_type=SampleType.ANNOTATION,
                parent_collection_id=root.collection_id,
            ),
        )


def test_create__root_collections_with_same_name_fails(test_db: Session) -> None:
    # Create a root collection
    collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
    )

    # Creating another root collection with the same name should fail
    with pytest.raises(ValueError, match="Collection with name 'root' already exists."):
        collection_resolver.create(
            session=test_db,
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE),
        )
