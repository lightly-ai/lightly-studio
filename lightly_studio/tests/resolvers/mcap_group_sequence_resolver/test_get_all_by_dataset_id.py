"""Tests for listing indexed recordings of a dataset."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver
from tests.helpers_resolvers import create_collection


def test_get_all_by_dataset_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        recording_id=recording_id,
    )
    other = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    other_recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=other.dataset_id,
        uri="/bags/other.mcap",
        format_=RecordingFormat.MCAP,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=other.collection_id,
        recording_id=other_recording_id,
    )

    rows = mcap_group_sequence_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )

    assert len(rows) == 1
    assert rows[0].sample_id == sample_id
    assert rows[0].recording_id == recording_id
    assert rows[0].uri == "/bags/drive_001.mcap"
