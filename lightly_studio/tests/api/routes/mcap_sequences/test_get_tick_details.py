"""Tests for the MCAP sequence tick-details route."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver
from lightly_studio.services import recording_service
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture

_TIMESTAMP_NS = 1_000


def test_get_tick_details(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/0"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    assert body["recording_id"] == str(fixture.recording_id)
    assert body["seq_number"] == 0
    assert body["timestamp_ns"] == _TIMESTAMP_NS
    assert set(body["channels"].keys()) == {"front", "pcl_front"}
    assert body["channels"]["front"] == {
        "channel_id": 3,
        "group_component_name": "front",
        "log_time_ns": str(_TIMESTAMP_NS),
        "keyframe_log_time_ns": str(_TIMESTAMP_NS),
    }
    assert body["channels"]["pcl_front"] == {
        "channel_id": 7,
        "group_component_name": "pcl_front",
        "log_time_ns": str(_TIMESTAMP_NS + 1),
        "keyframe_log_time_ns": None,
    }
    assert body["annotations"] == []


def test_get_tick_details__target_frame_id(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture)
    spy = mocker.spy(recording_service, "get_tick_details")

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/0",
        params={"target_frame_id": "CABIN"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert spy.call_args.kwargs["target_frame_id"] == "CABIN"


def test_get_tick_details__transform_not_found(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        recording_service,
        "get_tick_details",
        side_effect=McapAccessError("No transform connects the frames."),
    )

    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/ticks/0",
        params={"target_frame_id": "CABIN"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json()["detail"] == "No transform connects the frames."


def test_get_tick_details__unknown_sequence(test_client: TestClient) -> None:
    response = test_client.get(f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/ticks/0")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick_details__wrong_dataset(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture)

    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{fixture.sample_id}/ticks/0"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick_details__unknown_seq_number(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/99"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def _add_tick(session: Session, fixture: McapSequenceFixture) -> None:
    """Index a single tick with a camera and a lidar channel into the fixture sequence."""
    camera = create_mcap(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=3,
        log_time_ns=_TIMESTAMP_NS,
        keyframe_log_time_ns=_TIMESTAMP_NS,
    )
    lidar = create_mcap(
        session=session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=_TIMESTAMP_NS + 1,
        keyframe_log_time_ns=None,
    )
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, lidar.sample_id}],
    )
    session.add(
        SampleSequenceLinkTable(
            sample_id=group_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=_TIMESTAMP_NS,
        )
    )
    session.commit()
