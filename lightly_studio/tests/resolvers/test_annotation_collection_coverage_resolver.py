from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
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


def test_sequence_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    sequence_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        recording_id=recording_id,
    )
    linked_sample_id = sample_resolver.create_many(
        session=db_session,
        samples=[SampleCreate(collection_id=collection.collection_id)],
    )[0]
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=linked_sample_id, sequence_sample_id=sequence_id, seq_number=0
        )
    )
    db_session.commit()
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=[linked_sample_id],
    )

    assert annotation_collection_coverage_resolver.sequence_sample_ids(
        session=db_session, annotation_collection_id=annotation_collection_id
    ) == {sequence_id}
