"""Tests for get_ticks."""

from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import sample_resolver
from lightly_studio.services import recording_service
from tests.resolvers.mcap_group_sequence_resolver import helpers


def test_get_ticks(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    sample_ids = sample_resolver.create_many(
        session=db_session,
        samples=[
            SampleCreate(collection_id=fixture.group_collection.collection_id),
            SampleCreate(collection_id=fixture.group_collection.collection_id),
        ],
    )
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=sample_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=1_000,
        )
    )
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=sample_ids[1],
            sequence_sample_id=fixture.sample_id,
            seq_number=1,
            timestamp_ns=2_000,
        )
    )
    db_session.commit()

    result = recording_service.get_ticks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )

    assert result is not None
    assert len(result.ticks) == 2
    assert result.ticks[0].seq_number == 0
    assert result.ticks[0].timestamp_ns == 1_000
    assert result.ticks[1].seq_number == 1
    assert result.ticks[1].timestamp_ns == 2_000


def test_get_ticks__no_ticks(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_ticks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )

    assert result is not None
    assert result.ticks == []


def test_get_ticks__unknown_sequence(db_session: Session) -> None:
    result = recording_service.get_ticks(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=uuid.uuid4(),
    )

    assert result is None


def test_get_ticks__wrong_dataset(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_ticks(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=fixture.sample_id,
    )

    assert result is None
