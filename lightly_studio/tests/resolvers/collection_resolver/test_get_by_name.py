from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_collection,
)


def test_get_by_name(db_session: Session) -> None:
    # Create two collections
    ds1 = create_collection(session=db_session, collection_name="ds1")
    create_collection(session=db_session, collection_name="ds2")

    # Exactly one collection with the name exists
    collection_fetched = collection_resolver.get_by_name(session=db_session, name="ds1")
    assert collection_fetched is not None
    assert collection_fetched.collection_id == ds1.collection_id
    assert collection_fetched.name == "ds1"

    # No collection with the name exists
    collection_fetched = collection_resolver.get_by_name(session=db_session, name="non_existing")
    assert collection_fetched is None
