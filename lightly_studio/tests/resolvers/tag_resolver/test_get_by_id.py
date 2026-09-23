from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_read_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag = create_tag(session=db_session, collection_id=collection_id)

    tag_read = tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id)
    assert tag_read is not None
    assert tag_read.tag_id == tag.tag_id
    assert tag_read.name == "example_tag"
