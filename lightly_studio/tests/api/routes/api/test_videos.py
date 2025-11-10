from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests.conftest import VideosTestData


@pytest.fixture
def dataset_id(create_videos_for_dataset: VideosTestData) -> UUID:
    return create_videos_for_dataset.dataset_id


def test_get_all_videos(test_client: TestClient, dataset_id: UUID) -> None:
    response = test_client.get(
        f"/api/datasets/{dataset_id}/videos/",
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    data = result["data"]

    assert result["total_count"] == 2
    assert data[0]["file_path_abs"].endswith("sample1.mp4")
    assert data[1]["file_path_abs"].endswith("sample2.mp4")
