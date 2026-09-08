"""Tests for video frames media streaming endpoints."""

from __future__ import annotations

import io
import wave
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path
from typing import cast

import av
import cv2
import fsspec
import numpy as np
import pytest
from av.video.stream import VideoStream
from fastapi.testclient import TestClient
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session

import lightly_studio.api.routes.video_frames_media as video_frames_media_module
import lightly_studio.utils.executor as executor_module
from lightly_studio.api.routes.video_frames_media import FrameTransformOptions
from lightly_studio.models.collection import SampleType
from lightly_studio.models.settings import GridViewThumbnailQualityType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_file, create_video_with_frames


def test_stream_frame_png_format(
    media_test_client: TestClient,
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

    response = media_test_client.get(f"/frames/media/{frame_sample_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "Cache-Control" in response.headers
    assert "Content-Length" in response.headers

    # Verify it's a valid PNG (starts with PNG signature)
    image_data = response.content
    assert image_data.startswith(b"\x89PNG\r\n\x1a\n")


def test_stream_frame_high_returns_resized_jpeg(
    media_test_client: TestClient,
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

    response = media_test_client.get(
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
    media_test_client: TestClient,
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

    response = media_test_client.get(
        f"/frames/media/{video_with_frames.frame_sample_ids[0]}",
        params={"quality": "high"},
    )

    assert response.status_code == 400


@pytest.fixture(autouse=True)
def clear_container_cache() -> Iterator[None]:
    yield
    cache = getattr(video_frames_media_module._thread_local, "container_cache", {})
    for _, resources in cache.values():
        resources.close()
    cache.clear()


@pytest.fixture
def variable_rate_video(tmp_path: Path) -> Path:
    path = tmp_path / "variable.mkv"
    with av.open(str(path), mode="w") as container:
        stream = cast(VideoStream, container.add_stream("ffv1", rate=25))
        stream.width, stream.height = 32, 16
        stream.pix_fmt = "bgr0"
        stream.time_base = Fraction(1, 1000)
        stream.codec_context.time_base = Fraction(1, 1000)
        for index, pts in enumerate([100, 140, 220, 260, 400]):
            pixels = np.full((16, 32, 3), index * 40, dtype=np.uint8)
            pixels[:8, :16] = (255, 0, 0)
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            frame.pts, frame.time_base = pts, Fraction(1, 1000)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return path


@pytest.mark.parametrize("pts", [220, -1, 221])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_process_video_frame_exact_frame(
    variable_rate_video: Path,
    pts: int,
    rotation: int,
) -> None:
    # Includes missing/unmatched PTS and a nonzero start time at variable frame rate.
    buffer, media_type = video_frames_media_module._process_video_frame(
        video_path=str(variable_rate_video),
        frame_number=2,
        frame_timestamp_pts=pts,
        rotation_deg=rotation,
        transform=FrameTransformOptions(GridViewThumbnailQualityType.RAW, None, None),
    )
    expected = np.full((16, 32, 3), 80, dtype=np.uint8)
    expected[:8, :16] = (255, 0, 0)
    assert media_type == "image/png"
    np.testing.assert_array_equal(
        np.asarray(Image.open(io.BytesIO(buffer))), np.rot90(expected, k=rotation // 90)
    )


def test_decode_video_frame_seeks_backwards(variable_rate_video: Path) -> None:
    for index, pts in [(4, 400), (0, 100), (3, 260), (3, 260)]:
        frame = video_frames_media_module._decode_video_frame(
            video_path=str(variable_rate_video),
            frame_number=index,
            frame_timestamp_pts=pts,
        )
        assert frame.pts == pts
        assert frame.to_ndarray(format="rgb24")[-1, -1, 0] == index * 40


def test_decode_video_frame_failed_seek(variable_rate_video: Path, mocker: MockerFixture) -> None:
    container = video_frames_media_module._get_cached_container(str(variable_rate_video))
    unseekable = mocker.Mock(streams=container.streams)
    unseekable.seek.side_effect = av.error.InvalidDataError(1, "Cannot seek")
    mocker.patch.object(
        video_frames_media_module, "_get_cached_container", side_effect=[unseekable, container]
    )
    frame = video_frames_media_module._decode_video_frame(
        video_path=str(variable_rate_video),
        frame_number=2,
        frame_timestamp_pts=220,
    )
    assert frame.pts == 220


@pytest.mark.parametrize(
    ("bounds", "expected"), [((None, 4), (8, 4)), ((8, None), (8, 4)), ((64, 64), (32, 16))]
)
def test_resize_frame(bounds: tuple[int | None, int | None], expected: tuple[int, int]) -> None:
    result = video_frames_media_module._resize_frame(
        image=Image.new("RGB", (32, 16)),
        max_width=bounds[0],
        max_height=bounds[1],
    )
    assert result.size == expected


def test_decode_video_frame_invalid_index(variable_rate_video: Path) -> None:
    with pytest.raises(ValueError, match="No frame at index 20"):
        video_frames_media_module._decode_video_frame(
            video_path=str(variable_rate_video),
            frame_number=20,
            frame_timestamp_pts=-1,
        )


def test_get_cached_container_reuses_cached(variable_rate_video: Path) -> None:
    first = video_frames_media_module._get_cached_container(str(variable_rate_video))
    assert video_frames_media_module._get_cached_container(str(variable_rate_video)) is first


@pytest.mark.parametrize("reset", [False, True])
def test_get_cached_container_closes_files(
    variable_rate_video: Path,
    mocker: MockerFixture,
    reset: bool,
) -> None:
    fs = fsspec.filesystem("memory")
    mocker.patch.object(fsspec.core, "url_to_fs", return_value=(fs, "video"))
    files = [io.BytesIO(variable_rate_video.read_bytes()) for _ in range(5)]
    mocker.patch.object(fs, "open", side_effect=files)
    first = video_frames_media_module._get_cached_container("first")
    close = mocker.spy(video_frames_media_module._thread_local.container_cache["first"][1], "close")
    if reset:
        video_frames_media_module._get_cached_container(video_path="first", reset=True)
    else:
        for index in range(4):
            video_frames_media_module._get_cached_container(str(index))
    close.assert_called_once()
    assert files[0].closed
    with pytest.raises((AssertionError, ValueError), match=r"not open|closed"):
        next(first.decode(video=0))


@pytest.mark.parametrize("audio_only", [False, True])
def test_get_cached_container_failed_open_closes_file(
    mocker: MockerFixture,
    audio_only: bool,
) -> None:
    fs = fsspec.filesystem("memory")
    file = io.BytesIO(b"not a video")
    if audio_only:
        file = io.BytesIO()
        with wave.open(file, mode="wb") as audio:
            audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 800)
        file.seek(0)
    mocker.patch.object(fsspec.core, "url_to_fs", return_value=(fs, "broken"))
    mocker.patch.object(fs, "open", return_value=file)
    with pytest.raises((av.FFmpegError, ValueError)):
        video_frames_media_module._get_cached_container("broken")
    assert file.closed
    assert "broken" not in video_frames_media_module._thread_local.container_cache


@pytest.mark.parametrize("protocol", ["gs", "gcs", "s3", "file"])
def test_get_cached_container_remote_cache(
    variable_rate_video: Path,
    mocker: MockerFixture,
    protocol: str,
) -> None:
    fs = fsspec.filesystem("memory")
    mocker.patch.object(fsspec.core, "url_to_fs", return_value=(fs, "video"))
    open_file = mocker.patch.object(
        fs, "open", return_value=io.BytesIO(variable_rate_video.read_bytes())
    )
    container = video_frames_media_module._get_cached_container(f"{protocol}://video")
    assert next(container.decode(video=0)).pts == 100
    if protocol == "file":
        open_file.assert_called_once_with(path="video", mode="rb")
    else:
        open_file.assert_called_once_with(
            path="video",
            mode="rb",
            block_size=256 * 2**10,
            cache_type="blockcache",
            cache_options={"maxblocks": 4},
        )


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
    media_test_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Test streaming multiple frames from the same video uses caching."""
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
    frame_ids = video_with_frames.frame_sample_ids[:3]

    responses = []
    for frame_id in frame_ids:
        response = media_test_client.get(
            f"/frames/media/{frame_id}",
            params={"quality": "high", "max_width": 80, "max_height": 80},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        responses.append(response)

    # All should succeed (caching helps with performance)
    assert len(responses) == 3
    assert all(r.status_code == 200 for r in responses)
