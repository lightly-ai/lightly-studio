from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests.resolvers.video_resolver.helpers import create_videos_to_fake_dataset


def test_get_all_videos(test_client: TestClient, db_session: Session) -> None:
    videos = create_videos_to_fake_dataset(db_session=db_session)
    dataset_id = videos[0].sample.dataset_id

    response = test_client.get(
        f"/api/datasets/{dataset_id}/video/",
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


def test_get_video_by_id(test_client: TestClient, db_session: Session) -> None:
    videos = create_videos_to_fake_dataset(db_session=db_session)
    dataset_id = videos[0].sample.dataset_id
    sample_id = videos[0].sample_id
    response = test_client.get(
        f"/api/datasets/{dataset_id}/video/{sample_id}",
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert UUID(result["sample_id"]) == sample_id
    assert result["file_path_abs"].endswith("sample1.mp4")
