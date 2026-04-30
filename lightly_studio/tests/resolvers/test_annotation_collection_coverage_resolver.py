from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_add_many__inserts_rows(db_session: Session) -> None:
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
        for i in range(3)
    ]

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[s.sample_id for s in samples],
    )

    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
    )
    assert covered == {s.sample_id for s in samples}


def test_add_many__is_idempotent(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    sample = create_image(session=db_session, collection_id=parent_collection.collection_id)

    for _ in range(3):
        annotation_collection_coverage_resolver.add_many(
            session=db_session,
            annotation_collection_id=annotation_collection_id,
            parent_sample_ids=[sample.sample_id],
        )

    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
    )
    assert covered == {sample.sample_id}


def test_add_many__mixed_new_and_existing(db_session: Session) -> None:
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
        for i in range(3)
    ]

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[samples[0].sample_id],
    )
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[s.sample_id for s in samples],
    )

    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
    )
    assert covered == {s.sample_id for s in samples}


def test_add_many__empty_input_is_noop(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[],
    )

    covered = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_id
    )
    assert covered == []


def test_add_many__deduplicates_within_input(db_session: Session) -> None:
    parent_collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=parent_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    sample = create_image(session=db_session, collection_id=parent_collection.collection_id)

    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[sample.sample_id, sample.sample_id, sample.sample_id],
    )

    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
    )
    assert covered == {sample.sample_id}
