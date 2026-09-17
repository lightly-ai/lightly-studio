"""Tests for adding samples to a sequence in bulk."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sequence_resolver
from tests.resolvers.sequence_resolver import helpers


def test_add_samples(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )

    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(
                sample_id=sample_ids[0], seq_number=0, timestamp_ns=1785699091646722462
            ),
            SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=1),
        ],
    )

    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    assert [link.sample_id for link in links] == sample_ids
    assert [link.seq_number for link in links] == [0, 1]
    assert links[0].timestamp_ns == 1785699091646722462
    assert links[1].timestamp_ns is None


def test_add_samples__orders_by_seq_number(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )

    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=1),
            SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=0),
        ],
    )

    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    assert [link.sample_id for link in links] == [sample_ids[1], sample_ids[0]]


def test_add_samples__empty(db_session: Session) -> None:
    sequence_sample_id, _ = helpers.create_sequence_and_samples(session=db_session, sample_count=0)

    sequence_resolver.add_samples(
        session=db_session, sequence_sample_id=sequence_sample_id, links=[]
    )

    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    assert links == []


def test_add_samples__duplicate_seq_number(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )

    with pytest.raises(IntegrityError):
        sequence_resolver.add_samples(
            session=db_session,
            sequence_sample_id=sequence_sample_id,
            links=[
                SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0),
                SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=0),
            ],
        )
    db_session.rollback()


def test_add_samples__duplicate_seq_number_across_calls(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0)],
    )

    with pytest.raises(IntegrityError):
        sequence_resolver.add_samples(
            session=db_session,
            sequence_sample_id=sequence_sample_id,
            links=[SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=0)],
        )
    db_session.rollback()


def test_add_samples__negative_seq_number(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=2
    )

    with pytest.raises(ValueError, match="must not be negative"):
        sequence_resolver.add_samples(
            session=db_session,
            sequence_sample_id=sequence_sample_id,
            links=[
                SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0),
                SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=-1),
            ],
        )

    # The batch is checked before anything is written, so the valid link is not there.
    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    assert links == []


def test_add_samples__missing_sequence(db_session: Session) -> None:
    _, sample_ids = helpers.create_sequence_and_samples(session=db_session, sample_count=1)

    with pytest.raises(ValueError, match="Sequence with sample_id"):
        sequence_resolver.add_samples(
            session=db_session,
            sequence_sample_id=uuid4(),
            links=[SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0)],
        )


def test_add_samples__missing_sample(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=1
    )

    with pytest.raises(ValueError, match="Sample with sample_id"):
        sequence_resolver.add_samples(
            session=db_session,
            sequence_sample_id=sequence_sample_id,
            links=[
                SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0),
                SampleSequenceLinkCreate(sample_id=uuid4(), seq_number=1),
            ],
        )
