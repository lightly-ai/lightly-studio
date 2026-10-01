"""Tests for creating MCAP group sequences."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
)
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
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

    sequence = db_session.get(SequenceTable, sample_id)
    assert sequence is not None
    row = mcap_group_sequence_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert row is not None
    assert row.sample_id == sample_id
    assert row.recording_id == recording_id
    sample = sample_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert sample is not None
    assert sample.collection_id == collection.collection_id


def test_create__missing_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    with pytest.raises(ValueError, match=r"Collection with id .* not found"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=uuid.uuid4(),
            recording_id=recording_id,
        )


def test_create__non_sequence_collection(db_session: Session) -> None:
    image_col = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=image_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    with pytest.raises(ValueError, match="is having sample type 'image', expected 'sequence'"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=image_col.collection_id,
            recording_id=recording_id,
        )


def test_create__missing_recording(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    with pytest.raises(ValueError, match=r"Recording with id .* not found"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=collection.collection_id,
            recording_id=uuid.uuid4(),
        )
