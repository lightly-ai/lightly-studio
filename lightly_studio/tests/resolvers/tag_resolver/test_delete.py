from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_delete_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag = create_tag(session=db_session, collection_id=collection_id)

    # Delete the tag
    tag_resolver.delete(session=db_session, tag_id=tag.tag_id)

    # assert tag was deleted
    tag_deleted = tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id)
    assert tag_deleted is None


def test_delete_tag__removes_sample_links(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag = create_tag(session=db_session, collection_id=collection_id)
    image_1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample1.png"
    )
    image_2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample2.png"
    )

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image_1.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image_2.sample)

    tag_resolver.delete(session=db_session, tag_id=tag.tag_id)

    tag_deleted = tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id)
    assert tag_deleted is None
    assert image_1.sample.tags == []
    assert image_2.sample.tags == []
