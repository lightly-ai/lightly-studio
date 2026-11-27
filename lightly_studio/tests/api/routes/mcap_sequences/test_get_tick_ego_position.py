"""Tests for the MCAP sequence tick ego-position route."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.mcap_sequence_ticks import EgoPositionFrames, TickEgoPositionView
from lightly_studio.services import recording_service


def test_get_tick_ego_position(test_client: TestClient, mocker: MockerFixture) -> None:
    dataset_id = uuid.uuid4()
    sequence_id = uuid.uuid4()
    service = mocker.patch.object(
        recording_service,
        "get_tick_ego_position",
        return_value=TickEgoPositionView(position=[1.0, 2.0, 3.0]),
    )

    response = test_client.get(
        f"/datasets/{dataset_id}/mcap-sequences/{sequence_id}/ticks/4/ego-position",
        params={"target_frame_id": "map", "ego_frame_id": "CABIN"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"position": [1.0, 2.0, 3.0]}
    service.assert_called_once_with(
        session=mocker.ANY,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        seq_number=4,
        frames=EgoPositionFrames(target_frame_id="map", ego_frame_id="CABIN"),
    )


def test_get_tick_ego_position__not_found(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(recording_service, "get_tick_ego_position", return_value=None)

    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/ticks/0/ego-position",
        params={"target_frame_id": "map", "ego_frame_id": "CABIN"},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick_ego_position__missing_frames(test_client: TestClient) -> None:
    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/ticks/0/ego-position"
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
