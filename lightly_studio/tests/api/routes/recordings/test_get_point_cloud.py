"""Tests for the point-cloud route."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api import status
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import collection_resolver, recording_resolver
from tests.core.mcap import helpers


@pytest.fixture
def mcap_path(tmp_path: Path) -> Path:
    return helpers.write_mcap(tmp_path / "recording.mcap")


@pytest.fixture
def dataset_id(db_session: Session) -> UUID:
    collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE),
    )
    return collection.dataset_id


@pytest.fixture
def recording_id(db_session: Session, dataset_id: UUID, mcap_path: Path) -> UUID:
    return recording_resolver.create(
        session=db_session, dataset_id=dataset_id, uri=str(mcap_path), format_=RecordingFormat.MCAP
    )


@pytest.fixture
def channel_id(mcap_path: Path) -> int:
    return _channel_id(mcap_path=mcap_path, topic_name=helpers.LIDAR_POINTS_TOPIC)


def test_get_point_cloud(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={"channel_id": channel_id, "timestamp_ns": timestamp_ns},
    )

    assert response.status_code == status.HTTP_STATUS_OK
    assert response.headers["content-type"] == "application/vnd.apache.arrow.stream"
    assert response.headers["cache-control"] == "public, max-age=604800"
    assert response.headers["x-frame-log-time-ns"] == str(timestamp_ns)
    assert response.content


def test_get_point_cloud__404_when_no_message(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={"channel_id": channel_id, "timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0] - 1},
    )
    assert response.status_code == status.HTTP_STATUS_NOT_FOUND


def test_get_point_cloud__404_on_unknown_channel(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID
) -> None:
    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={"channel_id": 999_999, "timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0]},
    )
    assert response.status_code == status.HTTP_STATUS_NOT_FOUND


def test_get_point_cloud__400_on_non_point_cloud_channel(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID, mcap_path: Path
) -> None:
    channel_id = _channel_id(mcap_path=mcap_path, topic_name=helpers.CAMERA_VIDEO_TOPIC)

    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={"channel_id": channel_id, "timestamp_ns": helpers.VIDEO_LOG_TIMES_NS[0]},
    )

    assert response.status_code == status.HTTP_STATUS_BAD_REQUEST


def test_get_point_cloud__target_frame(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={
            "channel_id": channel_id,
            "timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0],
            "target_frame_id": helpers.LIDAR_FRAME_ID,
        },
    )

    assert response.status_code == status.HTTP_STATUS_OK
    assert response.content


def test_get_point_cloud__400_on_unconnected_target_frame(
    test_client: TestClient, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    # The recording has no `/tf` topic and no static transforms are stored.
    response = test_client.get(
        _point_cloud_url(dataset_id, recording_id),
        params={
            "channel_id": channel_id,
            "timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0],
            "target_frame_id": "map",
        },
    )

    assert response.status_code == status.HTTP_STATUS_BAD_REQUEST
    assert "map" in response.json()["detail"]


def _point_cloud_url(dataset_id: UUID, recording_id: UUID) -> str:
    return f"/datasets/{dataset_id}/recordings/{recording_id}/point-cloud"


def _channel_id(mcap_path: Path, topic_name: str) -> int:
    with McapFileReader(mcap_path) as reader:
        return next(topic.channel_id for topic in reader.get_topics() if topic.name == topic_name)
