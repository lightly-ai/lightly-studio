"""Tests for the MCAP sequence list endpoint."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver
from tests.helpers_resolvers import create_collection


def test_list_mcap_sequences(test_client: TestClient, db_session: Session) -> None:
    """Returns MCAP sequences with sample counts."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    seq_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/list",
        params={"cursor": 0, "limit": 10},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 1
    assert len(result["data"]) == 1
    assert result["data"][0]["sample_id"] == str(seq_id)
    assert result["data"][0]["recording_id"] == str(recording_id)
    assert result["data"][0]["sample_count"] == 0
    assert result["nextCursor"] is None


def test_list_mcap_sequences__empty_collection(
    test_client: TestClient, db_session: Session
) -> None:
    """Returns empty result for a collection with no sequences."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/list",
        params={"cursor": 0, "limit": 10},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 0
    assert result["data"] == []
    assert result["nextCursor"] is None


def test_list_mcap_sequences__pagination(test_client: TestClient, db_session: Session) -> None:
    """Cursor pagination returns correct pages and nextCursor."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/list",
        params={"cursor": 0, "limit": 2},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 3
    assert len(result["data"]) == 2
    assert result["nextCursor"] == 2

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/list",
        params={"cursor": 2, "limit": 2},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 3
    assert len(result["data"]) == 1
    assert result["nextCursor"] is None


def test_list_mcap_sequences__filter(test_client: TestClient, db_session: Session) -> None:
    """Returns only the MCAP sequences that match the filter."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_ids = _create_sequences(
        session=db_session, collection_id=seq_col.collection_id, dataset_id=seq_col.dataset_id
    )

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/list",
        params={"cursor": 0, "limit": 10},
        json={
            "filter": {
                "filter_type": "mcap_sequence",
                "sample_filter": {"sample_ids": [str(seq_ids[1])]},
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 1
    assert [sequence["sample_id"] for sequence in result["data"]] == [str(seq_ids[1])]


def test_get_mcap_sequence_sample_ids(test_client: TestClient, db_session: Session) -> None:
    """Returns the sample IDs of the MCAP sequences that match the filter."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_ids = _create_sequences(
        session=db_session, collection_id=seq_col.collection_id, dataset_id=seq_col.dataset_id
    )

    response = test_client.post(
        f"/api/collections/{seq_col.collection_id}/mcap-sequences/sample_ids",
        json={
            "filter": {
                "filter_type": "mcap_sequence",
                "sample_filter": {"sample_ids": [str(seq_ids[0])]},
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [str(seq_ids[0])]


def _create_sequences(session: Session, collection_id: UUID, dataset_id: UUID) -> list[UUID]:
    """Create two MCAP sequences of one recording."""
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    return [
        mcap_group_sequence_resolver.create(
            session=session, collection_id=collection_id, recording_id=recording_id
        )
        for _ in range(2)
    ]
