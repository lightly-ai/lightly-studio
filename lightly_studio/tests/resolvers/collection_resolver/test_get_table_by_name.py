from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_get_table_by_name(db_session: Session) -> None:
    collection = create_collection(session=db_session, collection_name="ds1")

    assert (
        collection_resolver.get_table_by_name(
            session=db_session, name="ds1", parent_collection_id=None
        )
        == collection
    )
    assert (
        collection_resolver.get_table_by_name(
            session=db_session, name="other", parent_collection_id=None
        )
        is None
    )
