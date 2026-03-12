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
    collection_fetched = collection_resolver.get_by_name(
        session=db_session, name="ds1", parent_collection_id=None
    )
    assert collection_fetched is not None
    assert collection_fetched.collection_id == ds1.collection_id
    assert collection_fetched.name == "ds1"
    assert collection_fetched.parent_collection_id is None


def test_get_by_name_root_not_found(db_session: Session) -> None:
    # No root collection with the name exists
    collection_fetched = collection_resolver.get_by_name(
        session=db_session, name="non_existing", parent_collection_id=None
    )
    assert collection_fetched is None


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
    collection_fetched = collection_resolver.get_by_name(
        session=db_session, name=child_name, parent_collection_id=ds1.collection_id
    )
    assert collection_fetched is not None
    assert collection_fetched.collection_id == child1.collection_id
    assert collection_fetched.name == child_name
    assert collection_fetched.parent_collection_id == ds1.collection_id

    # Find another child collection by name and its parent_collection_id
    collection_fetched = collection_resolver.get_by_name(
        session=db_session, name=child_name, parent_collection_id=ds2.collection_id
    )
    assert collection_fetched is not None
    assert collection_fetched.collection_id == child2.collection_id
    assert collection_fetched.name == child_name
    assert collection_fetched.parent_collection_id == ds2.collection_id


def test_get_by_name_child_not_found(db_session: Session) -> None:
    # Create a root collection
    ds1 = create_collection(session=db_session, collection_name="ds1")

    # No child collection with the name exists for the given parent
    collection_fetched = collection_resolver.get_by_name(
        session=db_session, name="ds1", parent_collection_id=ds1.collection_id
    )
    assert collection_fetched is None


def test_get_by_name_parent_not_found(db_session: Session) -> None:
    # Parent ID does not exist
    with pytest.raises(ValueError, match="Parent collection with id"):
        collection_resolver.get_by_name(
            session=db_session, name="child", parent_collection_id=uuid.uuid4()
        )
