"""Tests for reading the samples of a sequence."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import sequence_resolver
from tests.resolvers.sequence_resolver import helpers


def test_get_sample_links__empty(db_session: Session) -> None:
    sequence_sample_id, _ = helpers.create_sequence_and_samples(session=db_session, sample_count=0)

    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )

    assert links == []
