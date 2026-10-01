from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_add_tag_to_sample(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    image = create_image(session=db_session, collection_id=collection_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)

    assert image.sample.tags.index(tag) == 0
