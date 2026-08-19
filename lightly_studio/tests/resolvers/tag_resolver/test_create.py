import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_create_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="example_tag")
    assert tag.name == "example_tag"


def test_create_tag__unique_tag_name(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create_tag(session=db_session, collection_id=collection_id, tag_name="example_tag")

    # trying to create a tag with the same name results in an IntegrityError
    with pytest.raises(IntegrityError):
        tag_resolver.create(
            session=db_session,
            tag=TagCreate(
                collection_id=collection_id,
                name="example_tag",
                kind="sample",
            ),
        )
    db_session.rollback()
