from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_count_samples_per_tag(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag_a = create_tag(session=db_session, collection_id=collection_id, tag_name="a")
    tag_b = create_tag(session=db_session, collection_id=collection_id, tag_name="b")
    create_tag(session=db_session, collection_id=collection_id, tag_name="c")
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(3)
    ]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_a.tag_id, sample_ids=[i.sample_id for i in images]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_b.tag_id, sample_ids=[images[0].sample_id]
    )

    counts = tag_resolver.count_samples_per_tag(
        session=db_session,
        collection_id=collection_id,
        sample_ids_query=select(SampleTable.sample_id).where(
            col(SampleTable.collection_id) == collection_id
        ),
    )

    # Tag "c" has no samples, so it is omitted.
    assert counts == {tag_a.tag_id: 3, tag_b.tag_id: 1}


def test_count_samples_per_tag__only_counts_query_samples(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag_a = create_tag(session=db_session, collection_id=collection_id, tag_name="a")
    tag_b = create_tag(session=db_session, collection_id=collection_id, tag_name="b")
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(3)
    ]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_a.tag_id, sample_ids=[i.sample_id for i in images]
    )
    # Tag "b" sits only on the sample outside the query.
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_b.tag_id, sample_ids=[images[2].sample_id]
    )
    query = select(SampleTable.sample_id).where(
        col(SampleTable.sample_id).in_([images[0].sample_id, images[1].sample_id])
    )

    counts = tag_resolver.count_samples_per_tag(
        session=db_session, collection_id=collection_id, sample_ids_query=query
    )

    assert counts == {tag_a.tag_id: 2}
