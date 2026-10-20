"""Tests for get_keyframes in mcap_group_sequence_resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.mcap_group_sequence import McapSequenceKeyframe
from lightly_studio.resolvers import mcap_group_sequence_resolver
from tests.resolvers.mcap_group_sequence_resolver import helpers


def test_get_keyframes(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    # (camera log time, keyframe log time): only 300 and 100 are keyframes.
    helpers.add_mcap_ticks_to_sequence(
        session=db_session,
        fixture=fixture,
        ticks=[(300, 300), (200, 100), (100, 100)],
    )

    keyframes = mcap_group_sequence_resolver.get_keyframes(
        session=db_session,
        sequence_sample_ids=[fixture.sample_id],
        video_frame_collection_id=fixture.slots["front"].collection_id,
    )

    assert keyframes == {
        fixture.sample_id: [
            McapSequenceKeyframe(channel_id=3, log_time_ns=100),
            McapSequenceKeyframe(channel_id=3, log_time_ns=300),
        ]
    }


def test_get_keyframes__other_slot(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    helpers.add_mcap_ticks_to_sequence(session=db_session, fixture=fixture, ticks=[(100, 100)])

    # The point cloud slot has no keyframe.
    keyframes = mcap_group_sequence_resolver.get_keyframes(
        session=db_session,
        sequence_sample_ids=[fixture.sample_id],
        video_frame_collection_id=fixture.slots["pcl_front"].collection_id,
    )

    assert keyframes == {}


def test_get_keyframes__empty(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    keyframes = mcap_group_sequence_resolver.get_keyframes(
        session=db_session,
        sequence_sample_ids=[],
        video_frame_collection_id=fixture.slots["front"].collection_id,
    )

    assert keyframes == {}
