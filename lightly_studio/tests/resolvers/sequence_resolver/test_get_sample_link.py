"""Tests for reading a single tick of a sequence."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sequence_resolver
from tests.resolvers.sequence_resolver import helpers


def test_get_sample_link(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0, timestamp_ns=1_000),
            SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=1, timestamp_ns=2_000),
        ],
    )

    link = sequence_resolver.get_sample_link(
        session=db_session, sequence_sample_id=sequence_sample_id, seq_number=1
    )

    assert link is not None
    assert link.sample_id == sample_ids[1]
    assert link.seq_number == 1
    assert link.timestamp_ns == 2_000


def test_get_sample_link__unknown_seq_number(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=1
    )
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0)],
    )

    link = sequence_resolver.get_sample_link(
        session=db_session, sequence_sample_id=sequence_sample_id, seq_number=99
    )

    assert link is None


def test_get_sample_link__unknown_sequence(db_session: Session) -> None:
    link = sequence_resolver.get_sample_link(
        session=db_session, sequence_sample_id=uuid4(), seq_number=0
    )

    assert link is None
