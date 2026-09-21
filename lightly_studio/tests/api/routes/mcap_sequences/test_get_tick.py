"""Tests for the MCAP sequence single-tick detail route."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.mcap import McapCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver, mcap_resolver
from tests.resolvers.mcap_group_sequence_resolver.helpers import (
    McapSequenceFixture,
    create_mcap_sequence,
)

_T0 = 1_000_000_000
_T1 = 1_000_050_000


def _add_group_tick(
    session: Session,
    fixture: McapSequenceFixture,
    seq_number: int,
    log_time_ns: int,
) -> None:
    """Index one complete group tick (camera + lidar) into the fixture sequence."""
    camera_sample_id = mcap_resolver.create_many(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        samples=[
            McapCreate(
                channel_id=3,
                log_time_ns=log_time_ns,
                capture_timestamp_ns=log_time_ns,
                keyframe_log_time_ns=log_time_ns,
            )
        ],
    )[0]
    lidar_sample_id = mcap_resolver.create_many(
        session=session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        samples=[
            McapCreate(
                channel_id=7,
                log_time_ns=log_time_ns + 1,
                capture_timestamp_ns=log_time_ns + 1,
                keyframe_log_time_ns=None,
            )
        ],
    )[0]
    group_sample_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera_sample_id, lidar_sample_id}],
    )
    session.add(
        SampleSequenceLinkTable(
            sample_id=group_sample_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=seq_number,
            timestamp_ns=log_time_ns,
        )
    )
    session.commit()


def test_get_tick(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    _add_group_tick(session=db_session, fixture=fixture, seq_number=0, log_time_ns=_T0)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/0"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    assert body["seq_number"] == 0
    assert body["timestamp_ns"] == _T0
    assert body["recording_id"] == str(fixture.recording_id)

    channels = body["channels"]
    assert set(channels.keys()) == {"front", "pcl_front"}

    front = channels["front"]
    assert front["channel_id"] == 3
    assert front["log_time_ns"] == _T0
    assert front["keyframe_log_time_ns"] == _T0

    pcl = channels["pcl_front"]
    assert pcl["channel_id"] == 7
    assert pcl["log_time_ns"] == _T0 + 1
    assert pcl["keyframe_log_time_ns"] is None


def test_get_tick__second_tick(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    _add_group_tick(session=db_session, fixture=fixture, seq_number=0, log_time_ns=_T0)
    _add_group_tick(session=db_session, fixture=fixture, seq_number=1, log_time_ns=_T1)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/1"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    assert body["seq_number"] == 1
    assert body["timestamp_ns"] == _T1
    assert body["channels"]["front"]["log_time_ns"] == _T1


def test_get_tick__seq_number_not_found(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks/99"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick__unknown_sequence(test_client: TestClient) -> None:
    response = test_client.get(f"/datasets/{uuid4()}/mcap-sequences/{uuid4()}/ticks/0")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick__wrong_dataset(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    _add_group_tick(session=db_session, fixture=fixture, seq_number=0, log_time_ns=_T0)

    response = test_client.get(f"/datasets/{uuid4()}/mcap-sequences/{fixture.sample_id}/ticks/0")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
