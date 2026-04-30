"""Tests for image media streaming endpoints."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlmodel import Session

import lightly_studio.utils.executor as executor_module
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection, create_image


def test_stream_image_raw_returns_original_content_type(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that raw image requests keep the original file bytes and content type."""
    image_path = tmp_path / "test_image.png"
    PILImage.new("RGB", (320, 240), color="red").save(image_path)

    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(image_path),
        width=320,
        height=240,
    )

    response = test_client.get(f"/images/sample/{image.sample_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_stream_image_high_returns_jpeg_with_resized_bounds(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that high quality requests resize and encode as JPEG."""
    image_path = tmp_path / "test_image.png"
    PILImage.new("RGB", (400, 200), color="blue").save(image_path)

    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(image_path),
        width=400,
        height=200,
    )

    response = test_client.get(
        f"/images/sample/{image.sample_id}",
        params={"quality": "high", "max_width": 100, "max_height": 100},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8\xff")

    decoded = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[1] == 100
    assert decoded.shape[0] == 50


def test_stream_image_high_does_not_upscale_small_images(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that high quality requests do not upscale small images."""
    image_path = tmp_path / "small_image.png"
    PILImage.new("RGB", (40, 20), color="green").save(image_path)

    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(image_path),
        width=40,
        height=20,
    )

    response = test_client.get(
        f"/images/sample/{image.sample_id}",
        params={"quality": "high", "max_width": 200, "max_height": 200},
    )

    decoded = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[1] == 40
    assert decoded.shape[0] == 20


def test_stream_image_high_requires_bounds(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that transformed thumbnails require at least one bound."""
    image_path = tmp_path / "test_image.png"
    PILImage.new("RGB", (320, 240), color="red").save(image_path)

    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(image_path),
        width=320,
        height=240,
    )

    response = test_client.get(
        f"/images/sample/{image.sample_id}",
        params={"quality": "high"},
    )

    assert response.status_code == 400


def test_stream_image_sample_not_found(
    test_client: TestClient,
) -> None:
    """Test that a missing sample ID returns 404."""
    response = test_client.get("/images/sample/nonexistent-id")

    assert response.status_code == 404


def test_stream_image_file_not_found(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Test that a sample pointing to a missing file returns 404."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/nonexistent/path/image.png",
        width=100,
        height=100,
    )

    response = test_client.get(f"/images/sample/{image.sample_id}")

    assert response.status_code == 404


def test_get_media_executor_has_workers() -> None:
    """Test get_media_executor creates an executor with at least one worker."""
    executor_module._executors.clear()

    executor = executor_module.get_media_executor("image_thumbnail")

    assert executor is not None
    assert executor._max_workers >= 1
