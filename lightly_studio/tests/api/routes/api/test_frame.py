from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.dataset import SampleType
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_frame_resolver.helpers import create_video_with_frames
from tests.resolvers.video_resolver.helpers import VideoStub


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

    response = test_client.get(
        f"/api/datasets/{video_frame_dataset_id}/frame/",
        params={
            "offset": 0,
            "limit": 4,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    data = result["data"]

    assert result["total_count"] == 2
    assert data[0]["frame_number"] == 0
    assert UUID(data[0]["video"]["sample_id"]) == video_frame.video_sample_id

    assert data[1]["frame_number"] == 1
    assert UUID(data[1]["video"]["sample_id"]) == video_frame.video_sample_id
