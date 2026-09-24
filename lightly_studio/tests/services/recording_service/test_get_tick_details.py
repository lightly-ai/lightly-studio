"""Tests for get_tick_details."""

from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver
from lightly_studio.services import recording_service
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver import helpers


def test_get_tick_details(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
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
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=group_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=1_000,
        )
    )
    db_session.commit()

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
    )

    assert result is not None
    assert result.recording_id == fixture.recording_id
    assert result.seq_number == 0
    assert result.timestamp_ns == 1_000
    assert set(result.channels.keys()) == {"front", "pcl_front"}
    assert result.channels["front"].channel_id == 3
    assert result.channels["front"].group_component_name == "front"
    assert result.channels["front"].log_time_ns == "1000"
    assert result.channels["front"].keyframe_log_time_ns == "1000"
    assert result.channels["pcl_front"].channel_id == 7
    assert result.channels["pcl_front"].group_component_name == "pcl_front"
    assert result.channels["pcl_front"].log_time_ns == "1001"
    assert result.channels["pcl_front"].keyframe_log_time_ns is None


def test_get_tick_details__unknown_sequence(db_session: Session) -> None:
    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=uuid.uuid4(),
        seq_number=0,
    )

    assert result is None


def test_get_tick_details__wrong_dataset(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=fixture.sample_id,
        seq_number=0,
    )

    assert result is None


def test_get_tick_details__unknown_seq_number(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=99,
    )

    assert result is None
