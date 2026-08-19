from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_get_or_create_sample_tag_by_name(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create an existing tag
    existing_tag = create_tag(
        session=db_session, collection_id=collection_id, tag_name="existing_tag"
    )

    # Case 1: Get existing tag
    result_tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=db_session, collection_id=collection_id, tag_name="existing_tag"
    )
    assert result_tag.tag_id == existing_tag.tag_id
    assert result_tag.name == "existing_tag"

    # Case 2: Create new tag
    new_tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=db_session, collection_id=collection_id, tag_name="new_tag"
    )
    assert new_tag.tag_id != existing_tag.tag_id
    assert new_tag.name == "new_tag"
    assert new_tag.collection_id == collection_id
    assert new_tag.kind == "sample"
