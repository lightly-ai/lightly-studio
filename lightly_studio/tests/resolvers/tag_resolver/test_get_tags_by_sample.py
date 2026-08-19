from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_get_tags_by_sample(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img_a = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    img_b = create_image(session=db_session, collection_id=cid, file_path_abs="b.png")

    tag_1 = create_tag(session=db_session, collection_id=cid, tag_name="tag_1")
    tag_2 = create_tag(session=db_session, collection_id=cid, tag_name="tag_2")

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_1.tag_id, sample=img_a.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_2.tag_id, sample=img_a.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_1.tag_id, sample=img_b.sample)

    result = tag_resolver.get_tags_by_sample(
        session=db_session, tag_ids=[tag_1.tag_id, tag_2.tag_id]
    )
    assert result[img_a.sample_id] == {tag_1.tag_id, tag_2.tag_id}
    assert result[img_b.sample_id] == {tag_1.tag_id}


def test_get_tags_by_sample__empty(db_session: Session) -> None:
    result = tag_resolver.get_tags_by_sample(session=db_session, tag_ids=[])
    assert result == {}


def test_get_tags_by_sample__no_memberships(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    tag = create_tag(session=db_session, collection_id=cid, tag_name="lonely")

    result = tag_resolver.get_tags_by_sample(session=db_session, tag_ids=[tag.tag_id])
    assert result == {}
