from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_count_by_collection_id__empty(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    assert (
        annotation_collection_coverage_resolver.count_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
        == 0
    )


def test_count_by_collection_id__matches_list_length(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    samples = [
        create_image(
            session=db_session,
            collection_id=parent_collection.collection_id,
            file_path_abs=f"/path/to/image_{i}.png",
        )
        for i in range(5)
    ]

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[s.sample_id for s in samples],
    )

    count = annotation_collection_coverage_resolver.count_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_id
    )
    listed = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_id
    )
    assert count == len(listed) == 5
