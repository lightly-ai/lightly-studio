"""Tests for video frames media streaming endpoints."""

from __future__ import annotations

from pathlib import Path

import cv2
from fastapi.testclient import TestClient
from sqlmodel import Session

import lightly_studio.api.routes.video_frames_media as video_frames_media_module
from lightly_studio.api.routes.video_frames_media import (
    _CAP_CACHE_SIZE,
    _get_cached_capture,
    get_thread_pool_executor,
)
from lightly_studio.models.collection import SampleType
from tests.core.test_add_videos import _create_temp_video
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_stream_frame_png_format(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that stream_frame returns PNG format when compressed=False."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create a temporary video file
    video_path = _create_temp_video(
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

    # Request frame without compression (default)
    response = test_client.get(
        f"/frames/media/{frame_sample_id}",
        params={"compressed": False},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "Cache-Control" in response.headers
    assert "Content-Length" in response.headers

    # Verify it's a valid PNG (starts with PNG signature)
    image_data = response.content
    assert image_data.startswith(b"\x89PNG\r\n\x1a\n")


def test_stream_frame_jpeg_format(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that stream_frame returns JPEG format when compressed=True."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create a temporary video file
    video_path = _create_temp_video(
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

    # Request frame with compression
    response = test_client.get(
        f"/frames/media/{frame_sample_id}",
        params={"compressed": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert "Cache-Control" in response.headers
    assert "Content-Length" in response.headers

    # Verify it's a valid JPEG (starts with JPEG signature)
    image_data = response.content
    assert image_data.startswith(b"\xff\xd8\xff")


def test_stream_frame_default_compressed_false(
    test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test that stream_frame defaults to PNG when compressed parameter is not provided."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    video_path = _create_temp_video(
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

    frame_sample_id = video_with_frames.frame_sample_ids[0]

    # Request frame without compressed parameter (should default to False)
    response = test_client.get(f"/frames/media/{frame_sample_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_get_cached_capture_creates_new(
    tmp_path: Path,
) -> None:
    """Test _get_cached_capture creates new VideoCapture when not cached."""
    video_path = _create_temp_video(
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
    video_path = _create_temp_video(
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
        video_path = _create_temp_video(
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
    video_path = _create_temp_video(
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


def test_get_thread_pool_executor_creates_singleton() -> None:
    """Test get_thread_pool_executor returns the same executor instance."""
    # Reset the global executor
    import lightly_studio.api.routes.video_frames_media as module

    module._thread_pool_executor = None

    executor1 = get_thread_pool_executor()
    executor2 = get_thread_pool_executor()

    assert executor1 is executor2, "Should return the same executor instance"


def test_get_thread_pool_executor_has_workers() -> None:
    """Test get_thread_pool_executor creates executor with workers."""
    import lightly_studio.api.routes.video_frames_media as module

    module._thread_pool_executor = None

    executor = get_thread_pool_executor()

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

    video_path = _create_temp_video(
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
            params={"compressed": True},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        responses.append(response)

    # All should succeed (caching helps with performance)
    assert len(responses) == 3
    assert all(r.status_code == 200 for r in responses)
