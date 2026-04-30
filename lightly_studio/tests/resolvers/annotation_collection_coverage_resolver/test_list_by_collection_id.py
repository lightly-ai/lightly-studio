from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_list_by_collection_id__empty(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    assert (
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
        == []
    )


def test_list_by_collection_id__isolates_collections(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_a = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="run_a",
    )
    annotation_collection_b = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="run_b",
    )
    samples = [
        create_image(
            session=db_session,
            collection_id=parent_collection.collection_id,
            file_path_abs=f"/path/to/image_{i}.png",
        )
        for i in range(3)
    ]

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_a,
        parent_sample_ids=[samples[0].sample_id, samples[1].sample_id],
    )
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_b,
        parent_sample_ids=[samples[2].sample_id],
    )

    covered_a = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_a
    )
    covered_b = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_b
    )
    assert set(covered_a) == {samples[0].sample_id, samples[1].sample_id}
    assert set(covered_b) == {samples[2].sample_id}
