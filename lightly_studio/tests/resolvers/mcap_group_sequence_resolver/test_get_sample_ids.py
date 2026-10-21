"""Tests for get_sample_ids in mcap_group_sequence_resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import create_collection


def test_get_sample_ids(db_session: Session) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_ids = _create_sequences(
        session=db_session, collection_id=seq_col.collection_id, dataset_id=seq_col.dataset_id
    )
    # A sequence of another collection is left out.
    other_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session, collection_id=other_col.collection_id, dataset_id=other_col.dataset_id
    )

    sample_ids = mcap_group_sequence_resolver.get_sample_ids(
        session=db_session, collection_id=seq_col.collection_id
    )

    assert sample_ids == set(seq_ids)


def test_get_sample_ids__filters(db_session: Session) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_ids = _create_sequences(
        session=db_session, collection_id=seq_col.collection_id, dataset_id=seq_col.dataset_id
    )

    sample_ids = mcap_group_sequence_resolver.get_sample_ids(
        session=db_session,
        collection_id=seq_col.collection_id,
        filters=McapSequenceFilter(sample_filter=SampleFilter(sample_ids=[seq_ids[1]])),
    )

    assert sample_ids == {seq_ids[1]}


def _create_sequences(session: Session, collection_id: UUID, dataset_id: UUID) -> list[UUID]:
    """Create two MCAP sequences of one recording."""
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    return [
        mcap_group_sequence_resolver.create(
            session=session, collection_id=collection_id, recording_id=recording_id
        )
        for _ in range(2)
    ]
