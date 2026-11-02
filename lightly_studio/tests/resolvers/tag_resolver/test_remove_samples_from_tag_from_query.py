from uuid import uuid4

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_remove_samples_from_tag_from_query(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(3)
    ]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image.sample_id for image in images]
    )

    query = select(SampleTable.sample_id).where(
        col(SampleTable.sample_id).in_([images[0].sample_id, images[1].sample_id])
    )
    result = tag_resolver.remove_samples_from_tag_from_query(
        session=db_session, tag_id=tag.tag_id, sample_ids_query=query
    )

    assert result is not None
    assert {sample.sample_id for sample in tag.samples} == {images[2].sample_id}


def test_remove_samples_from_tag_from_query__unknown_tag_returns_none(db_session: Session) -> None:
    query = select(SampleTable.sample_id)
    result = tag_resolver.remove_samples_from_tag_from_query(
        session=db_session, tag_id=uuid4(), sample_ids_query=query
    )

    assert result is None
