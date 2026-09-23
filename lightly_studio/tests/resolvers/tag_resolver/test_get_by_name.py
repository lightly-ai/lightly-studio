from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_get_by_name__scoped_to_collection(db_session: Session) -> None:
    collection_a = create_collection(session=db_session)
    collection_b = create_collection(session=db_session)
    tag_a = create_tag(
        session=db_session,
        collection_id=collection_a.collection_id,
        tag_name="shared_name",
    )
    create_tag(
        session=db_session,
        collection_id=collection_b.collection_id,
        tag_name="shared_name",
    )

    result = tag_resolver.get_by_name(
        session=db_session,
        tag_name="shared_name",
        collection_id=collection_a.collection_id,
    )

    assert result is not None
    assert result.tag_id == tag_a.tag_id
