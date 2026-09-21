"""Tests for the MCAP sequence tick-list route."""

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

_T0 = 1_000_000_000
_T1 = 1_000_050_000


def _add_ticks(session: Session, fixture: McapSequenceFixture) -> None:
    """Index two ticks into the fixture sequence."""
    for seq_number, (log_time_ns, keyframe_log_time_ns) in enumerate(
        [(_T0, _T0), (_T1, _T1)]
    ):
        camera_sample_id = mcap_resolver.create_many(
            session=session,
            collection_id=fixture.slots["front"].collection_id,
            samples=[
                McapCreate(
                    channel_id=3,
                    log_time_ns=log_time_ns,
                    capture_timestamp_ns=log_time_ns,
                    keyframe_log_time_ns=keyframe_log_time_ns,
                )
            ],
        )[0]
        session.add(
            SampleSequenceLinkTable(
                sample_id=camera_sample_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
                timestamp_ns=log_time_ns,
            )
        )
    session.commit()


def test_get_ticks(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    _add_ticks(session=db_session, fixture=fixture)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks"
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    ticks = body["ticks"]
    assert len(ticks) == 2
    assert ticks[0] == {"seq_number": 0, "timestamp_ns": _T0}
    assert ticks[1] == {"seq_number": 1, "timestamp_ns": _T1}


def test_get_ticks__empty_sequence(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/ticks"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"ticks": []}


def test_get_ticks__unknown_sequence(test_client: TestClient) -> None:
    response = test_client.get(f"/datasets/{uuid4()}/mcap-sequences/{uuid4()}/ticks")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_ticks__wrong_dataset(test_client: TestClient, db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)

    response = test_client.get(
        f"/datasets/{uuid4()}/mcap-sequences/{fixture.sample_id}/ticks"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
