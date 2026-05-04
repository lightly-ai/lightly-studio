"""Tests for video frames media streaming endpoints."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient
from sqlmodel import Session

import lightly_studio.api.routes.video_frames_media as video_frames_media_module
import lightly_studio.utils.executor as executor_module
from lightly_studio.api.routes.video_frames_media import (
    _CAP_CACHE_SIZE,
    _get_cached_capture,
)
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_file, create_video_with_frames


def test_stream_frame_png_format(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that stream_frame returns PNG format by default (quality=raw)."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create a temporary video file
    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    # Create video with frames in database
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(
            path=str(video_path),
            width=320,
            height=240,
            duration_s=5.0,
            fps=1.0,
        ),
    )

    frame_sample_id = video_with_frames.frame_sample_ids[0]

    response = test_client.get(f"/frames/media/{frame_sample_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "Cache-Control" in response.headers
    assert "Content-Length" in response.headers

    # Verify it's a valid PNG (starts with PNG signature)
    image_data = response.content
    assert image_data.startswith(b"\x89PNG\r\n\x1a\n")


def test_stream_frame_high_returns_resized_jpeg(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that high quality frame requests resize and encode as JPEG."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(
            path=str(video_path),
            width=320,
            height=240,
            duration_s=5.0,
            fps=1.0,
        ),
    )

    response = test_client.get(
        f"/frames/media/{video_with_frames.frame_sample_ids[0]}",
        params={"quality": "high", "max_width": 80, "max_height": 80},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"

    decoded = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[1] == 80
    assert decoded.shape[0] == 60


def test_stream_frame_high_requires_bounds(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that quality=high without bounds returns 400."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(
            path=str(video_path),
            width=320,
            height=240,
            duration_s=5.0,
            fps=1.0,
        ),
    )

    response = test_client.get(
        f"/frames/media/{video_with_frames.frame_sample_ids[0]}",
        params={"quality": "high"},
    )

    assert response.status_code == 400


def test_get_cached_capture_creates_new(
    tmp_path: Path,
) -> None:
    """Test _get_cached_capture creates new VideoCapture when not cached."""
    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    cap = _get_cached_capture(str(video_path))

    assert cap is not None
    assert isinstance(cap, cv2.VideoCapture)
    assert cap.isOpened()


def test_get_cached_capture_reuses_cached(
    tmp_path: Path,
) -> None:
    """Test _get_cached_capture reuses cached VideoCapture for same video."""
    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    # Get capture first time
    cap1 = _get_cached_capture(str(video_path))
    cap1_id = id(cap1)

    # Get capture second time - should be same object
    cap2 = _get_cached_capture(str(video_path))
    cap2_id = id(cap2)

    assert cap1_id == cap2_id, "VideoCapture should be reused from cache"


def test_get_cached_capture_lru_eviction(
    tmp_path: Path,
) -> None:
    """Test _get_cached_capture evicts least recently used entries when cache is full."""
    # Create multiple video files
    video_paths = []
    for i in range(_CAP_CACHE_SIZE + 2):  # Create more than cache size
        video_path = create_video_file(
            output_path=tmp_path / f"test_video_{i}.mp4",
            width=320,
            height=240,
            num_frames=5,
            fps=1,
        )
        video_paths.append(str(video_path))

    # Fill cache to capacity
    for path in video_paths[:_CAP_CACHE_SIZE]:
        _get_cached_capture(path)

    # Access cache to verify size
    cache = video_frames_media_module._thread_local.cap_cache
    assert len(cache) == _CAP_CACHE_SIZE

    # Add one more - should evict the oldest
    _get_cached_capture(video_paths[_CAP_CACHE_SIZE])

    # Cache should still be at max size
    assert len(cache) == _CAP_CACHE_SIZE

    # The first video should be evicted (oldest)
    assert video_paths[0] not in cache


def test_get_cached_capture_handles_stale_entry(
    tmp_path: Path,
) -> None:
    """Test _get_cached_capture handles stale (closed) VideoCapture entries."""
    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    # Get and cache a capture
    cap1 = _get_cached_capture(str(video_path))
    assert cap1.isOpened()

    # Manually close it to simulate stale entry
    cap1.release()

    # Get capture again - should create new one since old is closed
    cap2 = _get_cached_capture(str(video_path))
    assert cap2.isOpened()
    assert id(cap1) != id(cap2), "Should create new VideoCapture for stale entry"


def test_get_media_executor_creates_singleton() -> None:
    """Test get_media_executor returns the same executor instance on repeated calls."""
    executor_module._executors.clear()

    executor1 = executor_module.get_media_executor("video_frame")
    executor2 = executor_module.get_media_executor("video_frame")

    assert executor1 is executor2, "Should return the same executor instance"


def test_get_media_executor_has_workers() -> None:
    """Test get_media_executor creates an executor with at least one worker."""
    executor_module._executors.clear()

    executor = executor_module.get_media_executor("video_frame")

    assert executor is not None
    assert executor._max_workers >= 1


def test_stream_frame_multiple_frames_same_video(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test streaming multiple frames from the same video uses caching."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    video_path = create_video_file(
        output_path=tmp_path / "test_video.mp4",
        width=320,
        height=240,
        num_frames=5,
        fps=1,
    )

    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(
            path=str(video_path),
            width=320,
            height=240,
            duration_s=5.0,
            fps=1.0,
        ),
    )

    # Request multiple frames from the same video
    frame_ids = video_with_frames.frame_sample_ids[:3]

    responses = []
    for frame_id in frame_ids:
        response = test_client.get(
            f"/frames/media/{frame_id}",
            params={"quality": "high", "max_width": 80, "max_height": 80},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        responses.append(response)

    # All should succeed (caching helps with performance)
    assert len(responses) == 3
    assert all(r.status_code == 200 for r in responses)
