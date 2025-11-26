from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import video_resolver
from tests.helpers_resolvers import create_dataset
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_all_videos(test_client: TestClient, db_session: Session) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=db_session,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/video/",
        params={
            "offset": 0,
            "limit": 2,
        },
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    data = result["data"]

    assert result["total_count"] == 2
    assert data[0]["file_path_abs"].endswith("sample1.mp4")
    assert data[1]["file_path_abs"].endswith("sample2.mp4")


def test_get_video_by_id(test_client: TestClient, db_session: Session) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=db_session,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )
    videos = video_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=dataset_id,
    ).samples

    sample_id = videos[0].sample_id

    response = test_client.get(
        f"/api/datasets/{dataset_id}/video/{sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert UUID(result["sample_id"]) == sample_id
    assert result["file_path_abs"].endswith("sample1.mp4")
