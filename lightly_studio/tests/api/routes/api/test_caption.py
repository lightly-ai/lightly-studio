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

    assert result["total_count"] == 40
    assert [f"Caption number {i}" for i in range(4)] == [
        caption["text"] for caption in result["data"][0]["captions"][:4]
    ]


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
    assert result["total_count"] == 40
    assert result["nextCursor"] == 3

    assert [f"Caption number {i}" for i in range(4)] == [
        caption["text"] for caption in result["data"][0]["captions"][:4]
    ]


def test_read_captions__last_page(
    test_client: TestClient,
    dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 2,
            "limit": 40,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 40
    assert result["nextCursor"] is None
    assert [f"Caption number {i}" for i in range(4)] == [
        caption["text"] for caption in result["data"][0]["captions"][:4]
    ]


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
