from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_collection,
)


def test_get_names_by_ids__returns_names_for_existing_ids(db_session: Session) -> None:
    ds1 = create_collection(session=db_session, collection_name="ds1")
    ds2 = create_collection(session=db_session, collection_name="ds2")
    ds3 = create_collection(session=db_session, collection_name="ds3")

    result = collection_resolver.get_names_by_ids(
        session=db_session,
        collection_ids=[ds1.collection_id, ds3.collection_id],
    )

    assert result == {
        ds1.collection_id: "ds1",
        ds3.collection_id: "ds3",
    }
    assert ds2.collection_id not in result


def test_get_names_by_ids__missing_ids_are_omitted(db_session: Session) -> None:
    ds1 = create_collection(session=db_session, collection_name="ds1")
    missing_id = uuid.uuid4()

    result = collection_resolver.get_names_by_ids(
        session=db_session,
        collection_ids=[ds1.collection_id, missing_id],
    )

    assert result == {ds1.collection_id: "ds1"}


def test_get_names_by_ids__empty_input(db_session: Session) -> None:
    create_collection(session=db_session, collection_name="ds1")

    result = collection_resolver.get_names_by_ids(session=db_session, collection_ids=[])

    assert result == {}
