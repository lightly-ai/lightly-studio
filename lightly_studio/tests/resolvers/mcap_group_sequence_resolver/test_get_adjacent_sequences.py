"""Tests for get_adjacent_sequences in mcap_group_sequence_resolver."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, insert

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver
from tests.helpers_resolvers import create_collection

SEQ_ID_A = UUID("00000000-0000-0000-0000-000000000001")
SEQ_ID_B = UUID("00000000-0000-0000-0000-000000000002")
SEQ_ID_C = UUID("00000000-0000-0000-0000-000000000003")


def test_get_adjacent_sequences(db_session: Session) -> None:
    """Orders by created_at before sample_id."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_C: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_A: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == SEQ_ID_C
    assert result.sample_id == SEQ_ID_A
    assert result.next_sample_id == SEQ_ID_B
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_sequences__tied_created_at_ordered_by_sample_id(
    db_session: Session,
) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    fixed_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_C: fixed_time,
            SEQ_ID_B: fixed_time,
            SEQ_ID_A: fixed_time,
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == SEQ_ID_A
    assert result.next_sample_id == SEQ_ID_C


def test_get_adjacent_sequences__ends_have_no_neighbour(db_session: Session) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
        },
    )

    first = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
    )
    last = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
    )

    assert first is not None
    assert first.previous_sample_id is None
    assert first.next_sample_id == SEQ_ID_B
    assert last is not None
    assert last.previous_sample_id == SEQ_ID_A
    assert last.next_sample_id is None


def test_get_adjacent_sequences__scoped_to_collection(db_session: Session) -> None:
    seq_col_a = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_col_b = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col_a,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    _create_sequences(
        session=db_session,
        collection=seq_col_b,
        created_at_by_sample_id={SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc)},
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col_a.collection_id,
    )
    other_collection_result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col_a.collection_id,
    )

    assert result is not None
    assert result.next_sample_id == SEQ_ID_C
    assert result.total_count == 2
    assert other_collection_result is None


def _create_sequences(
    session: Session,
    collection: CollectionTable,
    created_at_by_sample_id: dict[UUID, datetime],
) -> None:
    """Creates MCAP sequences with fixed IDs and creation times in one recording."""
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=f"/bags/{collection.collection_id}.mcap",
        format_=RecordingFormat.MCAP,
    )
    session.execute(
        insert(SampleTable).values(
            [
                {
                    "sample_id": sample_id,
                    "collection_id": collection.collection_id,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                for sample_id, created_at in created_at_by_sample_id.items()
            ]
        )
    )
    session.bulk_save_objects(
        [SequenceTable(sample_id=sample_id) for sample_id in created_at_by_sample_id]
    )
    session.bulk_save_objects(
        [
            McapGroupSequenceTable(sample_id=sample_id, recording_id=recording_id)
            for sample_id in created_at_by_sample_id
        ]
    )
    session.commit()
