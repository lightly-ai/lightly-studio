from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import video_resolver
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_dataset
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames, create_videos


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


def test_get_all_videos__with_width_filter(test_client: TestClient, db_session: Session) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=db_session,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4", width=800, height=1000),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/video/",
        params={
            "offset": 0,
            "limit": 2,
        },
        json={"filter": {"width": {"min": 800, "height": 1000}}},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    data = result["data"]

    assert result["total_count"] == 1
    assert data[0]["file_path_abs"].endswith("sample1.mp4")


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


def test_count_video_frame_annotations_by_video_dataset(
    test_client: TestClient, db_session: Session
) -> None:
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=db_session,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=db_session,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]

    # Create annotations labels
    car_label = create_annotation_label(
        session=db_session,
        annotation_label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        annotation_label_name="airplane",
    )

    create_annotation_label(
        session=db_session,
        annotation_label_name="house",
    )

    # Create annotations
    create_annotation(
        session=db_session,
        sample_id=video_frame_id,
        annotation_label_id=car_label.annotation_label_id,
        dataset_id=dataset_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        dataset_id=dataset_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        dataset_id=dataset_id,
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/video/annotations/count",
        params={
            "offset": 0,
            "limit": 2,
        },
        json={"filter": {"annotation_frames_label_ids": [str(airplane_label.annotation_label_id)]}},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert len(result) == 3
    assert result[0]["label"] == "airplane"
    assert result[0]["total"] == 1
    assert result[0]["filtered_count"] == 1

    assert result[1]["label"] == "car"
    assert result[1]["total"] == 1
    assert result[1]["filtered_count"] == 0

    assert result[2]["label"] == "house"
    assert result[2]["total"] == 0
    assert result[2]["filtered_count"] == 0
