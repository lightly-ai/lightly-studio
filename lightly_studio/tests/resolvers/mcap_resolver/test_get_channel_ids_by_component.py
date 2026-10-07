"""Tests for resolving channel IDs from indexed MCAP ticks."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver, mcap_resolver
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


def test_get_channel_ids_by_component__uses_indexed_tick_samples(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    camera = create_mcap(
        session=db_session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=2,
        log_time_ns=1_000,
        keyframe_log_time_ns=1_000,
    )
    lidar = create_mcap(
        session=db_session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=5,
        log_time_ns=1_001,
        keyframe_log_time_ns=None,
    )
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, lidar.sample_id}],
    )[0]
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=group_id,
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
        )
    )
    db_session.commit()

    result = mcap_resolver.get_channel_ids_by_component(
        session=db_session,
        sequence_id=fixture.sample_id,
    )

    assert result == {"front": 2, "pcl_front": 5}
