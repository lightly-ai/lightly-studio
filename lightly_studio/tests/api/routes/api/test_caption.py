from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.resolvers import caption_resolver
from tests.conftest import CaptionsTestData


@pytest.fixture
def dataset_id(captions_test_data: CaptionsTestData) -> UUID:
    return captions_test_data.datasets[0].dataset_id


@pytest.fixture
def dataset_id_other(captions_test_data: CaptionsTestData) -> UUID:
    return captions_test_data.datasets[1].dataset_id


def test_read_captions__first_page(
    test_client: TestClient,
    dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "offset": 0,
            "limit": 100,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 4
    assert [f"Caption number {i}" for i in range(4)] == [data["text"] for data in result["data"]]


def test_read_captions__middle_page(
    test_client: TestClient,
    dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 1,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 4
    assert result["nextCursor"] == 3
    assert [f"Caption number {i}" for i in range(1, 3)] == [data["text"] for data in result["data"]]


def test_read_captions__last_page(
    test_client: TestClient,
    dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 2,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 4
    assert result["nextCursor"] is None
    assert [f"Caption number {i}" for i in range(2, 4)] == [data["text"] for data in result["data"]]


def test_read_captions__no_captions(
    test_client: TestClient,
    dataset_id_other: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id_other}/captions",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["data"] == []
    assert result["total_count"] == 0
    assert result["nextCursor"] is None


def test_update_caption_text(
    db_session: Session,
    test_client: TestClient,
    dataset_id: UUID,
    captions_test_data: CaptionsTestData,
) -> None:
    # Update the text of a caption.
    caption_id = captions_test_data.captions[0].caption_id
    new_text = "updated text"
    response = test_client.put(
        f"/api/datasets/{dataset_id!s}/captions/{caption_id!s}",
        json=new_text,
    )

    # Verify that the response includes the updated caption.
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == new_text

    # Verify that the db entry changed by fetching it via the get endpoint.
    updated_caption = caption_resolver.get_by_ids(db_session, caption_ids=[caption_id])[0]
    assert updated_caption.text == new_text


def test_get_caption(test_client: TestClient, captions_test_data: CaptionsTestData) -> None:
    caption_id = captions_test_data.captions[0].caption_id
    text_db = captions_test_data.captions[0].text
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions/{caption_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == text_db


def test_delete_caption(
    test_client: TestClient,
    dataset_id: UUID,
    captions_test_data: CaptionsTestData,
) -> None:
    caption_id = captions_test_data.captions[0].caption_id

    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/captions/{caption_id}")
    assert delete_response.status_code == HTTP_STATUS_OK
    assert delete_response.json() == {"status": "deleted"}

    # Try to delete again and expect a 404
    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/captions/{caption_id}")
    assert delete_response.status_code == HTTP_STATUS_NOT_FOUND
    assert delete_response.json() == {"detail": "Caption not found"}
