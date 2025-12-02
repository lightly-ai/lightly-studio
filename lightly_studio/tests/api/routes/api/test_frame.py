from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.dataset import SampleType
from tests.helpers_resolvers import create_dataset
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_all_frames(
    test_client: TestClient,
    db_session: Session,
) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    video_frame = create_video_with_frames(
        session=db_session,
        dataset_id=dataset_id,
        video=VideoStub(path="video1.mp4", duration_s=1, fps=2),
    )

    video_frame_dataset_id = video_frame.video_frames_dataset_id

    response = test_client.post(
        f"/api/datasets/{video_frame_dataset_id}/frame/",
        params={
            "offset": 0,
            "limit": 4,
        },
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    data = result["data"]

    assert result["total_count"] == 2

    assert data[0]["frame_number"] == 0
    assert UUID(data[0]["video"]["sample_id"]) == video_frame.video_sample_id
    assert data[0]["video"]["file_path_abs"] == "video1.mp4"

    assert data[1]["frame_number"] == 1
    assert UUID(data[1]["video"]["sample_id"]) == video_frame.video_sample_id
    assert data[1]["video"]["file_path_abs"] == "video1.mp4"


def test_get_all_frames__with_video_id_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)

    video_frames = create_video_with_frames(
        session=db_session,
        dataset_id=dataset.dataset_id,
        video=VideoStub(path="video1.mp4", duration_s=1, fps=2),
    )

    create_video_with_frames(
        session=db_session,
        dataset_id=dataset.dataset_id,
        video=VideoStub(path="video2.mp4", duration_s=1, fps=2),
    )

    response = test_client.post(
        f"/api/datasets/{video_frames.video_frames_dataset_id}/frame/",
        params={"offset": 0, "limit": 4},
        json={"filter": {"video_id": str(video_frames.video_sample_id)}},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    data = result["data"]

    assert len(data) == 2

    assert data[0]["frame_number"] == 0
    assert data[0]["video"]["sample_id"] == str(video_frames.video_sample_id)

    assert data[1]["frame_number"] == 1
    assert data[1]["video"]["sample_id"] == str(video_frames.video_sample_id)


def test_get_table_fields_bounds(test_client: TestClient, db_session: Session) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    video_frames_dataset_id = create_video_with_frames(
        session=db_session,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4", fps=5, duration_s=1),
    ).video_frames_dataset_id

    response = test_client.get(
        f"/api/datasets/{video_frames_dataset_id}/frame/bounds",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result is not None
    assert result["frame_number"]["min"] == 0
    assert result["frame_number"]["max"] == 4


def test_get_by_id(
    test_client: TestClient,
    db_session: Session,
) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    video_frames = create_video_with_frames(
        session=db_session,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/video1.mp4", duration_s=2.0, fps=1),
    )

    frame_sample_id = video_frames.frame_sample_ids[0]

    response = test_client.get(
        f"/api/datasets/{dataset_id}/frame/{frame_sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert UUID(result["sample_id"]) == frame_sample_id
    assert result["video"] is not None
    assert result["video"]["file_path_abs"] == "/path/to/video1.mp4"
