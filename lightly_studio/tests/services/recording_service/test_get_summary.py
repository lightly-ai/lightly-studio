"""Tests for building an MCAP sequence's channel summary from the database."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.services.recording_service import get_mcap_sequence_summary
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
    assert [channel.group_component_name for channel in summary.camera_channels] == ["front"]
    assert [channel.group_component_name for channel in summary.lidar_channels] == ["pcl_front"]

    camera_channel = summary.camera_channels[0]
    assert camera_channel.channel_id == 3
    assert camera_channel.frame_id == "main"

    lidar_channel = summary.lidar_channels[0]
    assert lidar_channel.channel_id == 7
    assert lidar_channel.frame_id == "livox_front_left"


def test_get_mcap_sequence_summary__unknown_sequence(db_session: Session) -> None:
    summary = get_mcap_sequence_summary(session=db_session, dataset_id=uuid4(), sequence_id=uuid4())

    assert summary is None


def test_get_mcap_sequence_summary__wrong_dataset(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    summary = get_mcap_sequence_summary(
        session=db_session, dataset_id=uuid4(), sequence_id=fixture.sample_id
    )

    assert summary is None
