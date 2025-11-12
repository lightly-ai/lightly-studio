from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
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
    test_client: TestClient, dataset_id: UUID, captions_test_data: CaptionsTestData
) -> None:
    # Update the text of a caption
    caption_id = captions_test_data.captions[0].caption_id
    new_text = "updated text"
    response = test_client.put(
        f"/api/datasets/{dataset_id!s}/captions/{caption_id!s}",
        json=new_text,
    )

    # Verify that the response gives the updated caption
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == new_text

    # Verify that the db entry changed by fetching it via get
    get_response = test_client.get(f"/api/datasets/{dataset_id}/captions")
    assert get_response.status_code == HTTP_STATUS_OK
    updated_caption = next(
        caption
        for caption in get_response.json()["data"]
        if caption["caption_id"] == str(caption_id)
    )
    assert updated_caption["text"] == new_text
