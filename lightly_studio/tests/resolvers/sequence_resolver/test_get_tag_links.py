"""Tests for reading the tags on the samples of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sample_resolver, sequence_resolver, tag_resolver
from tests.helpers_resolvers import create_tag
from tests.resolvers.sequence_resolver import helpers


def test_get_tag_links(db_session: Session) -> None:
    sequence_sample_id, sample_ids = _create_sequence_with_ticks(session=db_session, tick_count=3)
    collection_id = _collection_id(session=db_session, sample_id=sample_ids[0])
    tag_b = create_tag(session=db_session, collection_id=collection_id, tag_name="b")
    tag_a = create_tag(session=db_session, collection_id=collection_id, tag_name="a")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_b.tag_id, sample_ids=[sample_ids[2], sample_ids[0]]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_a.tag_id, sample_ids=[sample_ids[1]]
    )

    links = sequence_resolver.get_tag_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )

    assert [(tag.name, seq_number) for tag, seq_number in links] == [
        ("a", 1),
        ("b", 0),
        ("b", 2),
    ]


def test_get_tag_links__no_tags(db_session: Session) -> None:
    sequence_sample_id, _ = _create_sequence_with_ticks(session=db_session, tick_count=2)

    links = sequence_resolver.get_tag_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )

    assert links == []


def test_get_tag_links__ignores_other_samples(db_session: Session) -> None:
    sequence_sample_id, _ = _create_sequence_with_ticks(session=db_session, tick_count=1)
    _, other_sample_ids = _create_sequence_with_ticks(session=db_session, tick_count=1)
    for tagged_sample_id in [other_sample_ids[0], sequence_sample_id]:
        tag = create_tag(
            session=db_session,
            collection_id=_collection_id(session=db_session, sample_id=tagged_sample_id),
            tag_name="occluded",
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session, tag_id=tag.tag_id, sample_ids=[tagged_sample_id]
        )

    links = sequence_resolver.get_tag_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )

    assert links == []


def _create_sequence_with_ticks(session: Session, tick_count: int) -> tuple[UUID, list[UUID]]:
    """Create a sequence whose ticks are `tick_count` new samples at seq numbers 0, 1, …."""
    sequence_sample_id, sample_ids = helpers.create_sequence_and_samples(
        session=session, sample_count=tick_count
    )
    sequence_resolver.add_samples(
        session=session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=sample_id, seq_number=seq_number)
            for seq_number, sample_id in enumerate(sample_ids)
        ],
    )
    return sequence_sample_id, sample_ids


def _collection_id(session: Session, sample_id: UUID) -> UUID:
    sample = sample_resolver.get_by_id(session=session, sample_id=sample_id)
    assert sample is not None
    return sample.collection_id
