from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_add_many__basic_and_idempotent(db_session: Session) -> None:
    """Test that add_many inserts rows and is idempotent (safe to call repeatedly)."""
    collection = create_collection(session=db_session)
    cov_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    samples = [
        create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/img_{i}.png",
        )
        for i in range(3)
    ]

    # First call: insert all samples.
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=cov_id,
        parent_sample_ids=[s.sample_id for s in samples],
    )
    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=cov_id
        )
    )
    assert covered == {s.sample_id for s in samples}

    # Second call: add subset (some overlap). Should not create duplicates.
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=cov_id,
        parent_sample_ids=[samples[0].sample_id, samples[-1].sample_id],
    )
    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=cov_id
        )
    )
    assert covered == {s.sample_id for s in samples}

    # Third call: empty list is a no-op.
    annotation_collection_coverage_resolver.add_many(
        session=db_session, annotation_collection_id=cov_id, parent_sample_ids=[]
    )
    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=cov_id
        )
    )
    assert covered == {s.sample_id for s in samples}


def test_add_many__deduplicates_input(db_session: Session) -> None:
    """Test that add_many deduplicates within a single call (same ID passed multiple times)."""
    collection = create_collection(session=db_session)
    cov_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    sample = create_image(session=db_session, collection_id=collection.collection_id)

    # Pass the same sample ID three times.
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=cov_id,
        parent_sample_ids=[sample.sample_id] * 3,
    )

    covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=cov_id
        )
    )
    assert covered == {sample.sample_id}
