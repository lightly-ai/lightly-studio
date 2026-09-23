"""Tests for the camera-frame route."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import collection_resolver, recording_resolver
from tests.core.mcap import helpers


@dataclass
class RecordingFixture:
    dataset_id: UUID
    recording_id: UUID
    channel_id: int
    mcap_path: Path


@pytest.fixture
def recording(db_session: Session, tmp_path: Path) -> RecordingFixture:
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    collection = collection_resolver.create(
        db_session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri=str(mcap_path),
        format_=RecordingFormat.MCAP,
    )
    with McapFileReader(mcap_path) as reader:
        channel_id = next(
            topic.channel_id
            for topic in reader.get_topics()
            if topic.name == helpers.CAMERA_VIDEO_TOPIC
        )
    return RecordingFixture(
        dataset_id=collection.dataset_id,
        recording_id=recording_id,
        channel_id=channel_id,
        mcap_path=mcap_path,
    )


def _camera_frame_url(dataset_id: UUID, recording_id: UUID) -> str:
    return f"/datasets/{dataset_id}/recordings/{recording_id}/camera-frame"


def test_get_camera_frame(
    test_client: TestClient, recording: RecordingFixture, mocker: MockerFixture
) -> None:
    mocker.patch.object(compressed_video, "from_decoded_message", return_value=b"\xff\xd8\xff")
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]

    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": recording.channel_id, "keyframe_timestamp_ns": keyframe_ns},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-frame-log-time-ns"] == str(keyframe_ns)
    assert response.content == b"\xff\xd8\xff"


def test_get_camera_frame__unknown_recording(test_client: TestClient) -> None:
    response = test_client.get(
        _camera_frame_url(uuid4(), uuid4()),
        params={"channel_id": 0, "keyframe_timestamp_ns": 0},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_camera_frame__unknown_channel(
    test_client: TestClient, recording: RecordingFixture
) -> None:
    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": 999_999, "keyframe_timestamp_ns": 0},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_camera_frame__etag_in_response(
    test_client: TestClient, recording: RecordingFixture, mocker: MockerFixture
) -> None:
    mocker.patch.object(compressed_video, "from_decoded_message", return_value=b"\xff\xd8\xff")
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]

    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": recording.channel_id, "keyframe_timestamp_ns": keyframe_ns},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["etag"] == f'"{keyframe_ns}-{recording.channel_id}-None-None-85"'


def test_get_camera_frame__400_on_mcap_access_error(
    test_client: TestClient, recording: RecordingFixture, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        compressed_video, "from_decoded_message", side_effect=McapAccessError("bad codec")
    )
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]

    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": recording.channel_id, "keyframe_timestamp_ns": keyframe_ns},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_get_camera_frame__304_on_matching_if_none_match(
    test_client: TestClient, recording: RecordingFixture, mocker: MockerFixture
) -> None:
    mocker.patch.object(compressed_video, "from_decoded_message", return_value=b"\xff\xd8\xff")
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]
    etag = f'"{keyframe_ns}-{recording.channel_id}-None-None-85"'

    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": recording.channel_id, "keyframe_timestamp_ns": keyframe_ns},
        headers={"if-none-match": etag},
    )

    assert response.status_code == 304
    assert response.content == b""


def test_get_camera_frame__200_on_mismatched_if_none_match(
    test_client: TestClient, recording: RecordingFixture, mocker: MockerFixture
) -> None:
    mocker.patch.object(compressed_video, "from_decoded_message", return_value=b"\xff\xd8\xff")
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]

    response = test_client.get(
        _camera_frame_url(recording.dataset_id, recording.recording_id),
        params={"channel_id": recording.channel_id, "keyframe_timestamp_ns": keyframe_ns},
        headers={"if-none-match": '"stale-etag"'},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert len(response.content) > 0
