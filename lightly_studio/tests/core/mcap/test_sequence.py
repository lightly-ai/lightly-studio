from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.core.mcap.sequence import McapSequence, McapSequenceEntry
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
)
from tests.helpers_resolvers import create_collection


class TestMcapSequence:
    def test_add_samples(self, db_session: Session) -> None:
        sequence, group_collection_id = _create_sequence(session=db_session)
        sample_ids = _create_samples(session=db_session, collection_id=group_collection_id, count=3)

        sequence.add_samples(
            entries=[
                McapSequenceEntry(
                    sample_id=sample_id, seq_number=index, timestamp_ns=1_000_000_000 + index
                )
                for index, sample_id in enumerate(sample_ids)
            ]
        )

        assert sequence.get_samples() == [
            McapSequenceEntry(sample_id=sample_ids[0], seq_number=0, timestamp_ns=1_000_000_000),
            McapSequenceEntry(sample_id=sample_ids[1], seq_number=1, timestamp_ns=1_000_000_001),
            McapSequenceEntry(sample_id=sample_ids[2], seq_number=2, timestamp_ns=1_000_000_002),
        ]

    def test_add_samples__ordered_by_seq_number(self, db_session: Session) -> None:
        sequence, group_collection_id = _create_sequence(session=db_session)
        sample_ids = _create_samples(session=db_session, collection_id=group_collection_id, count=2)

        # The entries are passed out of order, the sequence is read back in order.
        sequence.add_samples(
            entries=[
                McapSequenceEntry(sample_id=sample_ids[0], seq_number=1),
                McapSequenceEntry(sample_id=sample_ids[1], seq_number=0),
            ]
        )

        assert [entry.sample_id for entry in sequence.get_samples()] == [
            sample_ids[1],
            sample_ids[0],
        ]

    def test_add_samples__without_timestamp(self, db_session: Session) -> None:
        sequence, group_collection_id = _create_sequence(session=db_session)
        sample_ids = _create_samples(session=db_session, collection_id=group_collection_id, count=1)

        sequence.add_samples(entries=[McapSequenceEntry(sample_id=sample_ids[0], seq_number=0)])

        assert sequence.get_samples() == [
            McapSequenceEntry(sample_id=sample_ids[0], seq_number=0, timestamp_ns=None)
        ]

    def test_add_samples__empty(self, db_session: Session) -> None:
        sequence, _ = _create_sequence(session=db_session)

        sequence.add_samples(entries=[])

        assert sequence.get_samples() == []

    def test_add_samples__unknown_sample(self, db_session: Session) -> None:
        sequence, _ = _create_sequence(session=db_session)
        sample_id = uuid4()

        with pytest.raises(ValueError, match=f"Sample with sample_id {sample_id} not found"):
            sequence.add_samples(entries=[McapSequenceEntry(sample_id=sample_id, seq_number=0)])

    def test_add_samples__negative_seq_number(self, db_session: Session) -> None:
        sequence, group_collection_id = _create_sequence(session=db_session)
        sample_ids = _create_samples(session=db_session, collection_id=group_collection_id, count=1)

        with pytest.raises(ValueError, match="seq_number must not be negative, got -1"):
            sequence.add_samples(
                entries=[McapSequenceEntry(sample_id=sample_ids[0], seq_number=-1)]
            )

    def test_add_samples__slot_taken(self, db_session: Session) -> None:
        sequence, group_collection_id = _create_sequence(session=db_session)
        sample_ids = _create_samples(session=db_session, collection_id=group_collection_id, count=2)
        sequence.add_samples(entries=[McapSequenceEntry(sample_id=sample_ids[0], seq_number=0)])

        with pytest.raises(IntegrityError):
            sequence.add_samples(entries=[McapSequenceEntry(sample_id=sample_ids[1], seq_number=0)])
        db_session.rollback()

    def test_get_samples__empty(self, db_session: Session) -> None:
        sequence, _ = _create_sequence(session=db_session)

        assert sequence.get_samples() == []


def _create_sequence(session: Session) -> tuple[McapSequence, UUID]:
    """Create a sequence on a fresh dataset, and return it with its group collection."""
    root_collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    group_collection = create_collection(
        session=session,
        parent_collection_id=root_collection.collection_id,
        sample_type=SampleType.GROUP,
    )
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=root_collection.dataset_id,
        uri="/data/perception.mcap",
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=session,
        collection_id=root_collection.collection_id,
        recording_id=recording_id,
    )
    sequence = McapSequence(session=session, sample_id=sample_id, recording_id=recording_id)
    return sequence, group_collection.collection_id


def _create_samples(session: Session, collection_id: UUID, count: int) -> list[UUID]:
    """Create bare samples to put in the slots of a sequence."""
    return sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id) for _ in range(count)],
    )
