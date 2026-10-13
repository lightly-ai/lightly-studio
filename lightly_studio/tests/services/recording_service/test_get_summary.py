"""Tests for building an MCAP sequence's channel summary from the database."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver
from lightly_studio.services.recording_service import get_mcap_sequence_summary
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


def test_get_mcap_sequence_summary(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session, uri="/bags/drive_001.mcap")

    summary = get_mcap_sequence_summary(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )

    assert summary is not None
    assert summary.recording_id == fixture.recording_id
    assert summary.file_name == "drive_001.mcap"
    assert summary.reference_frames == []
    assert [channel.group_component_name for channel in summary.camera_channels] == ["front"]
    assert [channel.group_component_name for channel in summary.lidar_channels] == ["pcl_front"]

    camera_channel = summary.camera_channels[0]
    assert camera_channel.channel_id == 3
    assert camera_channel.frame_id == "main"

    lidar_channel = summary.lidar_channels[0]
    assert lidar_channel.channel_id == 7
    assert lidar_channel.frame_id == "livox_front_left"


def test_get_mcap_sequence_summary__uses_channel_ids_from_indexed_ticks(
    db_session: Session,
) -> None:
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

    summary = get_mcap_sequence_summary(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )

    assert summary is not None
    assert summary.camera_channels[0].channel_id == 2
    assert summary.lidar_channels[0].channel_id == 5


def test_get_mcap_sequence_summary__unknown_sequence(db_session: Session) -> None:
    summary = get_mcap_sequence_summary(session=db_session, dataset_id=uuid4(), sequence_id=uuid4())

    assert summary is None


def test_get_mcap_sequence_summary__wrong_dataset(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    summary = get_mcap_sequence_summary(
        session=db_session, dataset_id=uuid4(), sequence_id=fixture.sample_id
    )

    assert summary is None
