import pytest
from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_remove_sample_from_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    image = create_image(session=db_session, collection_id=collection_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)
    assert len(image.sample.tags) == 1
    assert image.sample.tags.index(tag) == 0

    # remove sample to tag
    tag_resolver.remove_tag_from_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)
    assert len(image.sample.tags) == 0
    with pytest.raises(ValueError, match="not in list"):
        image.sample.tags.index(tag)
