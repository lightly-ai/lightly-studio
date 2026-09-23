from uuid import uuid4

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_add_samples_to_tag_from_query__tags_only_query_matches(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(4)
    ]
    wanted = {images[0].sample_id, images[2].sample_id}

    query = select(SampleTable.sample_id).where(col(SampleTable.sample_id).in_(wanted))
    result = tag_resolver.add_samples_to_tag_from_query(
        session=db_session, tag_id=tag.tag_id, sample_ids_query=query
    )

    # Exactly the query's matches are linked (correct sample/tag wiring, no over-tagging).
    assert result is not None
    assert {sample.sample_id for sample in tag.samples} == wanted


def test_add_samples_to_tag_from_query__unknown_tag_returns_none(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id

    query = select(SampleTable.sample_id).where(col(SampleTable.collection_id) == collection_id)
    result = tag_resolver.add_samples_to_tag_from_query(
        session=db_session, tag_id=uuid4(), sample_ids_query=query
    )

    assert result is None
