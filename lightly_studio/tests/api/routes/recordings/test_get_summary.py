"""Tests for the MCAP sequence channel-summary route."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.mcap import McapCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import mcap_resolver
from tests.resolvers.mcap_group_sequence_resolver.helpers import (
    McapSequenceFixture,
    create_mcap_sequence,
)

_START_LOG_TIME_NS = 1_000_000_000  # 1 s epoch in nanoseconds


def _add_ticks(session: Session, fixture: McapSequenceFixture) -> None:
    """Index one tick per channel into the fixture sequence."""
    camera_sample_id = mcap_resolver.create_many(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        samples=[
            McapCreate(
                channel_id=3,
                log_time_ns=_START_LOG_TIME_NS,
                capture_timestamp_ns=_START_LOG_TIME_NS,
                keyframe_log_time_ns=_START_LOG_TIME_NS,
            )
        ],
    )[0]
    lidar_sample_id = mcap_resolver.create_many(
        session=session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        samples=[
            McapCreate(
                channel_id=7,
                log_time_ns=_START_LOG_TIME_NS + 1,
                capture_timestamp_ns=_START_LOG_TIME_NS + 1,
                keyframe_log_time_ns=None,
            )
        ],
    )[0]
    session.add(
        SampleSequenceLinkTable(
            sample_id=camera_sample_id,
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
        )
    )
    session.add(
        SampleSequenceLinkTable(
            sample_id=lidar_sample_id,
            sequence_sample_id=fixture.sample_id,
            seq_number=1,
        )
    )
    session.commit()


def test_get_summary(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session, uri="/bags/drive_001.mcap")

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/summary"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    assert body["recording_id"] == str(fixture.recording_id)
    assert body["format"] == "mcap"
    assert body["start_log_time_ns"] is None  # no ticks indexed in fixture
    assert [channel["group_component_name"] for channel in body["camera_channels"]] == ["front"]
    assert [channel["group_component_name"] for channel in body["lidar_channels"]] == ["pcl_front"]


def test_get_summary__with_indexed_ticks(test_client: TestClient, db_session: Session) -> None:
    """Summary with indexed ticks returns the earliest log time and correct channel IDs.

    start_log_time_ns and channel_id are the two values the 3D playground needs for
    initial rendering: start_log_time_ns becomes the timestamp_ns query param on the
    first camera-frame and lidar-frame requests, and channel_id identifies which channel
    to fetch within the bag.
    """
    fixture = create_mcap_sequence(session=db_session, uri="/bags/drive_001.mcap")
    _add_ticks(session=db_session, fixture=fixture)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/summary"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()

    assert body["start_log_time_ns"] == _START_LOG_TIME_NS

    camera_channels = body["camera_channels"]
    assert len(camera_channels) == 1
    assert camera_channels[0]["channel_id"] == 3
    assert camera_channels[0]["group_component_name"] == "front"

    lidar_channels = body["lidar_channels"]
    assert len(lidar_channels) == 1
    assert lidar_channels[0]["channel_id"] == 7
    assert lidar_channels[0]["group_component_name"] == "pcl_front"


def test_get_summary__unknown_sequence(test_client: TestClient) -> None:
    response = test_client.get(f"/datasets/{uuid4()}/mcap-sequences/{uuid4()}/summary")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_summary__wrong_dataset(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    response = test_client.get(f"/datasets/{uuid4()}/mcap-sequences/{fixture.sample_id}/summary")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
