from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_get_names_by_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    tag_a = create_tag(session=db_session, collection_id=cid, tag_name="alpha")
    tag_b = create_tag(session=db_session, collection_id=cid, tag_name="beta")

    result = tag_resolver.get_names_by_ids(session=db_session, tag_ids=[tag_a.tag_id, tag_b.tag_id])
    assert result == {tag_a.tag_id: "alpha", tag_b.tag_id: "beta"}


def test_get_names_by_ids__empty(db_session: Session) -> None:
    result = tag_resolver.get_names_by_ids(session=db_session, tag_ids=[])
    assert result == {}


def test_get_names_by_ids__unknown_id(db_session: Session) -> None:
    result = tag_resolver.get_names_by_ids(session=db_session, tag_ids=[uuid4()])
    assert result == {}
