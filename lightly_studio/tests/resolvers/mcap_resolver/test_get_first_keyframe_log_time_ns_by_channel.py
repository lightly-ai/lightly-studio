from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import mcap_resolver, sequence_resolver
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


@dataclass
class _TickSpec:
    slot_collection_id: uuid.UUID
    seq_number: int
    channel_id: int
    log_time_ns: int
    keyframe_log_time_ns: int | None


def _add_tick(session: Session, sequence_id: uuid.UUID, spec: _TickSpec) -> None:
    """Create an MCAP tick in a slot collection and link it to the sequence."""
    mcap = create_mcap(
        session=session,
        collection_id=spec.slot_collection_id,
        channel_id=spec.channel_id,
        log_time_ns=spec.log_time_ns,
        keyframe_log_time_ns=spec.keyframe_log_time_ns,
    )
    sequence_resolver.add_samples(
        session=session,
        sequence_sample_id=sequence_id,
        links=[SampleSequenceLinkCreate(sample_id=mcap.sample_id, seq_number=spec.seq_number)],
    )


def test_get_first_keyframe_log_time_ns_by_channel(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    front_collection_id = fixture.slots["front"].collection_id

    _add_tick(
        session=db_session,
        sequence_id=fixture.sample_id,
        spec=_TickSpec(
            slot_collection_id=front_collection_id,
            seq_number=0,
            channel_id=3,
            log_time_ns=100,
            keyframe_log_time_ns=90,
        ),
    )
    _add_tick(
        session=db_session,
        sequence_id=fixture.sample_id,
        spec=_TickSpec(
            slot_collection_id=front_collection_id,
            seq_number=1,
            channel_id=3,
            log_time_ns=200,
            keyframe_log_time_ns=180,
        ),
    )

    result = mcap_resolver.get_first_keyframe_log_time_ns_by_channel(
        session=db_session, sequence_id=fixture.sample_id
    )

    assert result == {3: 90}


def test_get_first_keyframe_log_time_ns_by_channel__multiple_channels(
    db_session: Session,
) -> None:
    fixture = create_mcap_sequence(session=db_session)

    _add_tick(
        session=db_session,
        sequence_id=fixture.sample_id,
        spec=_TickSpec(
            slot_collection_id=fixture.slots["front"].collection_id,
            seq_number=0,
            channel_id=3,
            log_time_ns=100,
            keyframe_log_time_ns=90,
        ),
    )
    _add_tick(
        session=db_session,
        sequence_id=fixture.sample_id,
        spec=_TickSpec(
            slot_collection_id=fixture.slots["pcl_front"].collection_id,
            seq_number=1,
            channel_id=7,
            log_time_ns=150,
            keyframe_log_time_ns=None,
        ),
    )

    result = mcap_resolver.get_first_keyframe_log_time_ns_by_channel(
        session=db_session, sequence_id=fixture.sample_id
    )

    # Channel 7 has no keyframe, so only channel 3 is returned.
    assert result == {3: 90}


def test_get_first_keyframe_log_time_ns_by_channel__no_ticks(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    result = mcap_resolver.get_first_keyframe_log_time_ns_by_channel(
        session=db_session, sequence_id=fixture.sample_id
    )

    assert result == {}


def test_get_first_keyframe_log_time_ns_by_channel__unknown_sequence(db_session: Session) -> None:
    result = mcap_resolver.get_first_keyframe_log_time_ns_by_channel(
        session=db_session, sequence_id=uuid.uuid4()
    )

    assert result == {}
