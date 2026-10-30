from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_get_names_by_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img_a = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    img_b = create_image(session=db_session, collection_id=cid, file_path_abs="b.png")
    img_untagged = create_image(session=db_session, collection_id=cid, file_path_abs="c.png")

    tag_beta = create_tag(session=db_session, collection_id=cid, tag_name="beta")
    tag_alpha = create_tag(session=db_session, collection_id=cid, tag_name="alpha")

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_beta.tag_id, sample=img_a.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_alpha.tag_id, sample=img_a.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_beta.tag_id, sample=img_b.sample)

    result = tag_resolver.get_names_by_sample_ids(
        session=db_session,
        sample_ids=[img_a.sample_id, img_b.sample_id, img_untagged.sample_id],
    )
    assert result == {img_a.sample_id: ["alpha", "beta"], img_b.sample_id: ["beta"]}


def test_get_names_by_sample_ids__empty(db_session: Session) -> None:
    result = tag_resolver.get_names_by_sample_ids(session=db_session, sample_ids=[])
    assert result == {}


def test_get_names_by_sample_ids__unknown_id(db_session: Session) -> None:
    result = tag_resolver.get_names_by_sample_ids(session=db_session, sample_ids=[uuid4()])
    assert result == {}
