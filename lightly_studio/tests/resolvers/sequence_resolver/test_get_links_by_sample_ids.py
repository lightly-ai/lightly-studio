from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sequence_resolver
from tests.resolvers.sequence_resolver import helpers


def test_get_links_by_sample_ids(db_session: Session) -> None:
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=db_session, sample_count=3
    )
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=sample_ids[0], seq_number=0, timestamp_ns=10),
            SampleSequenceLinkCreate(sample_id=sample_ids[1], seq_number=1, timestamp_ns=20),
            SampleSequenceLinkCreate(sample_id=sample_ids[2], seq_number=2, timestamp_ns=None),
        ],
    )
    unlinked_id = uuid4()

    result = sequence_resolver.get_links_by_sample_ids(
        session=db_session, sample_ids=[sample_ids[0], sample_ids[2], unlinked_id]
    )

    assert set(result) == {sample_ids[0], sample_ids[2]}
    assert result[sample_ids[0]].sequence_sample_id == sequence_sample_id
    assert result[sample_ids[0]].seq_number == 0
    assert result[sample_ids[0]].timestamp_ns == 10
    assert result[sample_ids[2]].seq_number == 2
    assert result[sample_ids[2]].timestamp_ns is None


def test_get_links_by_sample_ids__empty(db_session: Session) -> None:
    assert sequence_resolver.get_links_by_sample_ids(session=db_session, sample_ids=[]) == {}
