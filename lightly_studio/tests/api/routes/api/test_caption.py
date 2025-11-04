from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.image import ImageTable
from tests.conftest import CaptionsTestData


@pytest.fixture
def dataset_id(captions_test_data: CaptionsTestData) -> UUID:
    return captions_test_data.dataset_ids[0]


@pytest.fixture
def dataset_id_other(captions_test_data: CaptionsTestData) -> UUID:
    return captions_test_data.dataset_ids[1]


@pytest.fixture
def samples_with_captions(captions_test_data: CaptionsTestData) -> list[ImageTable]:
    return captions_test_data.samples


def test_read_captions__first_page(
    test_client: TestClient,
    dataset_id: UUID,
    samples_with_captions: list[ImageTable],
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 0,
            "limit": 4,
        },
    )

    assert response.status_code == HTTP_STATUS_OK

    result = response.json()
    samples = result["data"]

    assert result["total_count"] == 10

    assert samples[0]["captions"][0]["text"] == "Caption number 0"
    assert samples_with_captions[0].sample_id == UUID(samples[0]["sample_id"])

    assert samples[1]["captions"][0]["text"] == "Caption number 1"
    assert samples_with_captions[1].sample_id == UUID(samples[1]["sample_id"])

    assert samples[2]["captions"][0]["text"] == "Caption number 2"
    assert samples_with_captions[2].sample_id == UUID(samples[2]["sample_id"])

    assert samples[3]["captions"][0]["text"] == "Caption number 3"
    assert samples_with_captions[3].sample_id == UUID(samples[3]["sample_id"])


def test_read_captions__middle_page(
    test_client: TestClient,
    dataset_id: UUID,
    samples_with_captions: list[ImageTable],
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 4,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    samples = result["data"]

    assert result["total_count"] == 10
    assert result["nextCursor"] == 6

    assert samples[0]["captions"][0]["text"] == "Caption number 4"
    assert samples_with_captions[4].sample_id == UUID(samples[0]["sample_id"])

    assert samples[1]["captions"][0]["text"] == "Caption number 5"
    assert samples_with_captions[5].sample_id == UUID(samples[1]["sample_id"])


def test_read_captions__last_page(
    test_client: TestClient,
    dataset_id: UUID,
    samples_with_captions: list[ImageTable],
) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions",
        params={
            "cursor": 6,
            "limit": 4,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    samples = result["data"]

    assert result["total_count"] == 10
    assert result["nextCursor"] is None

    assert samples[0]["captions"][0]["text"] == "Caption number 6"
    assert samples_with_captions[6].sample_id == UUID(samples[0]["sample_id"])

    assert samples[1]["captions"][0]["text"] == "Caption number 7"
    assert samples_with_captions[7].sample_id == UUID(samples[1]["sample_id"])

    assert samples[2]["captions"][0]["text"] == "Caption number 8"
    assert samples_with_captions[8].sample_id == UUID(samples[2]["sample_id"])

    assert samples[3]["captions"][0]["text"] == "Caption number 9"
    assert samples_with_captions[9].sample_id == UUID(samples[3]["sample_id"])


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
