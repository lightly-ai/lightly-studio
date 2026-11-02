"""Tests for video media streaming endpoints."""

from __future__ import annotations

import fsspec
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


def test_serve_video_by_sample_id__access_error_without_strerror(
    media_test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an OSError without strerror logs its message and returns only its class name."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="s3://bucket/video.mp4"),
    )
    mocker.patch.object(
        fsspec.core,
        "url_to_fs",
        side_effect=OSError(
            "SSL validation failed for https://minio:9000/bucket [SSL: CERTIFICATE_VERIFY_FAILED]"
        ),
    )

    response = media_test_client.get(f"/videos/media/{video.sample_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Error accessing file s3://bucket/video.mp4: OSError"
    assert "https://minio:9000" in caplog.text
