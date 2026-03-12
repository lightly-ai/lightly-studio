from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_collection,
)


def test_get_by_name__root_success(db_session: Session) -> None:
    # Create two root collections
    ds1 = create_collection(session=db_session, collection_name="ds1")
    create_collection(session=db_session, collection_name="ds2")

    # Exactly one root collection with the name exists
    collection_id = collection_resolver.get_by_name(
        session=db_session, name="ds1", parent_collection_id=None
    )
    assert collection_id == ds1.collection_id


def test_get_by_name_root_not_found(db_session: Session) -> None:
    # No root collection with the name exists
    collection_id = collection_resolver.get_by_name(
        session=db_session, name="non_existing", parent_collection_id=None
    )
    assert collection_id is None


def test_get_by_name_child_success(db_session: Session) -> None:
    # Create two root collections
    ds1 = create_collection(session=db_session, collection_name="ds1")
    ds2 = create_collection(session=db_session, collection_name="ds2")

    # Create two child collections with the same name but different parents
    child_name = "child"
    child1 = create_collection(
        session=db_session, collection_name=child_name, parent_collection_id=ds1.collection_id
    )
    child2 = create_collection(
        session=db_session, collection_name=child_name, parent_collection_id=ds2.collection_id
    )

    # Find child collection by name and parent_collection_id
    collection_id1 = collection_resolver.get_by_name(
        session=db_session, name=child_name, parent_collection_id=ds1.collection_id
    )
    assert collection_id1 == child1.collection_id
    assert collection_id1 is not None
    collection = collection_resolver.get_by_id(session=db_session, collection_id=collection_id1)
    assert collection is not None
    assert collection.name == child_name
    assert collection.parent_collection_id == ds1.collection_id

    # Find another child collection by name and its parent_collection_id
    collection_id2 = collection_resolver.get_by_name(
        session=db_session, name=child_name, parent_collection_id=ds2.collection_id
    )
    assert collection_id2 == child2.collection_id
    assert collection_id2 is not None
    collection = collection_resolver.get_by_id(session=db_session, collection_id=collection_id2)
    assert collection is not None
    assert collection.name == child_name
    assert collection.parent_collection_id == ds2.collection_id


def test_get_by_name_child_not_found(db_session: Session) -> None:
    # Create a root collection
    ds1 = create_collection(session=db_session, collection_name="ds1")

    # No child collection with the name exists for the given parent
    collection_id = collection_resolver.get_by_name(
        session=db_session, name="ds1", parent_collection_id=ds1.collection_id
    )
    assert collection_id is None


def test_get_by_name_parent_not_found(db_session: Session) -> None:
    # Parent ID does not exist
    with pytest.raises(ValueError, match="Parent collection with id"):
        collection_resolver.get_by_name(
            session=db_session, name="child", parent_collection_id=uuid.uuid4()
        )
