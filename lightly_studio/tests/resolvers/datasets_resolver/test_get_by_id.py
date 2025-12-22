from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_collection,
)


def test_get_by_id(test_db: Session) -> None:
    # Create two collections
    ds1 = create_collection(session=test_db, collection_name="ds1")
    create_collection(session=test_db, collection_name="ds2")
    collection_id = ds1.collection_id

    # Fetch an existing collection
    collection_fetched = collection_resolver.get_by_id(session=test_db, collection_id=collection_id)
    assert collection_fetched is not None
    assert collection_fetched.collection_id == collection_id
    assert collection_fetched.name == "ds1"

    # Fetch a non-existing collection
    collection_fetched = collection_resolver.get_by_id(session=test_db, collection_id=UUID(int=123))
    assert collection_fetched is None
