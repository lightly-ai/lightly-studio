"""Tests for the get_tick_channels resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import group_resolver, mcap_resolver
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


def test_get_tick_channels(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    camera = create_mcap(
        session=db_session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=3,
        log_time_ns=1_000,
        keyframe_log_time_ns=1_000,
    )
    lidar = create_mcap(
        session=db_session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=1_001,
        keyframe_log_time_ns=None,
    )
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, lidar.sample_id}],
    )

    result = mcap_resolver.get_tick_channels(session=db_session, group_sample_id=group_ids[0])

    assert set(result.keys()) == {"front", "pcl_front"}
    assert result["front"].channel_id == 3
    assert result["front"].log_time_ns == 1_000
    assert result["front"].keyframe_log_time_ns == 1_000
    assert result["pcl_front"].channel_id == 7
    assert result["pcl_front"].log_time_ns == 1_001
    assert result["pcl_front"].keyframe_log_time_ns is None


def test_get_tick_channels__unknown_group(db_session: Session) -> None:
    result = mcap_resolver.get_tick_channels(session=db_session, group_sample_id=uuid4())

    assert result == {}
