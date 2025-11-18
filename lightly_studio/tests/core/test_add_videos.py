import os
from pathlib import Path
from unittest.mock import MagicMock

import av
import fsspec
import numpy as np
from av import container
from av.codec.context import ThreadType
from PIL import Image as PILImage
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core import add_videos
from lightly_studio.core.add_videos import (
    FrameExtractionContext,
    _configure_stream_threading,
    _create_video_frame_samples,
)
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoCreate
from lightly_studio.resolvers import dataset_resolver, video_frame_resolver, video_resolver
from tests.helpers_resolvers import create_dataset


def test_load_into_dataset_from_paths(db_session: Session, tmp_path: Path) -> None:
    dataset = create_dataset(db_session, sample_type=SampleType.VIDEO)
    # Create two temporary video files.
    first_video_path = _create_temp_video(
        output_path=tmp_path / "test_video_1.mp4",
        width=640,
        height=480,
        num_frames=30,
        fps=2.0,
    )
    second_video_path = _create_temp_video(
        output_path=tmp_path / "test_video_0.mp4",
        width=640,
        height=480,
        num_frames=30,
        fps=2.0,
    )
    video_sample_ids, frame_sample_ids = add_videos.load_into_dataset_from_paths(
        session=db_session,
        dataset_id=dataset.dataset_id,
        video_paths=[str(first_video_path), str(second_video_path)],
    )
    assert len(video_sample_ids) == 2
    assert len(frame_sample_ids) == 60

    # Check that video samples are created.
    videos = video_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    ).samples
    assert len(videos) == 2

    video = videos[0]
    assert video.file_name == "test_video_0.mp4"
    assert video.file_path_abs == str(second_video_path)
    video = videos[1]
    assert video.file_name == "test_video_1.mp4"
    assert video.file_path_abs == str(first_video_path)

    # Check the correct dataset hierarchy was created. There should be one extra dataset
    # created with the video frames.
    dataset_hierarchy = dataset_resolver.get_hierarchy(
        session=db_session,
        root_dataset_id=dataset.dataset_id,
    )
    assert len(dataset_hierarchy) == 2
    assert dataset_hierarchy[0].sample_type == SampleType.VIDEO
    assert dataset_hierarchy[1].sample_type == SampleType.VIDEO_FRAME

    video_frames = video_frame_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=dataset_hierarchy[1].dataset_id,
    ).samples
    assert len(video_frames) == 60


def test__create_video_frame_samples(db_session: Session, tmp_path: Path) -> None:
    """Test _create_video_frame_samples function directly."""
    dataset = create_dataset(db_session, sample_type=SampleType.VIDEO)

    # Create a temporary video file
    video_path = _create_temp_video(
        output_path=tmp_path / "test_video_frames.mp4",
        width=320,
        height=240,
        num_frames=2,
        fps=1.0,
    )

    # Create video sample in database
    video_sample_ids = video_resolver.create_many(
        session=db_session,
        dataset_id=dataset.dataset_id,
        samples=[
            VideoCreate(
                file_path_abs=str(video_path),
                file_name=video_path.name,
                width=320,
                height=240,
                duration_s=2.0,  # 2 frames / 1 fps = 2 seconds
                fps=1.0,
            )
        ],
    )
    assert len(video_sample_ids) == 1
    video_sample_id = video_sample_ids[0]

    # Create video frames dataset
    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=db_session, dataset_id=dataset.dataset_id
    )

    fs, fs_path = fsspec.core.url_to_fs(url=str(video_path))
    video_file = fs.open(path=fs_path, mode="rb")
    video_container = container.open(file=video_file)

    frame_sample_ids = _create_video_frame_samples(
        context=FrameExtractionContext(
            session=db_session,
            dataset_id=video_frames_dataset_id,
            video_sample_id=video_sample_id,
        ),
        video_container=video_container,
        video_channel=0,
    )

    # Verify all frames were created
    assert len(frame_sample_ids) == 2

    # Verify frames are in the database
    video_frames = video_frame_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=video_frames_dataset_id,
    ).samples
    assert len(video_frames) == 2

    # Verify frame properties
    assert video_frames[0].frame_number == 0
    assert video_frames[0].parent_sample_id == video_sample_id
    assert video_frames[0].frame_timestamp_s == 0
    assert video_frames[1].frame_number == 1
    assert video_frames[1].parent_sample_id == video_sample_id
    assert video_frames[1].frame_timestamp_s == 1
    video_container.close()
    video_file.close()


def _create_temp_video(
    output_path: Path,
    width: int = 640,
    height: int = 480,
    num_frames: int = 30,
    fps: float = 30.0,
) -> Path:
    """Create a temporary video file using PyAV for testing.

    Args:
        output_path: Path where the video file will be saved.
        width: Width of the video in pixels.
        height: Height of the video in pixels.
        num_frames: Number of frames to generate.
        fps: Frame rate of the video.

    Returns:
        The path to the created video file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Open output container
    output_container = av.open(str(output_path), mode="w")  # type: ignore[attr-defined]

    # Add video stream
    stream = output_container.add_stream("libx264", rate=fps)
    stream.width = width  # type: ignore[attr-defined]
    stream.height = height  # type: ignore[attr-defined]
    stream.pix_fmt = "yuv420p"  # type: ignore[attr-defined]

    # Generate simple solid color frames
    frame_data = np.zeros((height, width, 3), dtype=np.uint8)
    pil_image = PILImage.fromarray(frame_data, "RGB")

    for frame_num in range(num_frames):
        # Convert PIL Image to PyAV frame
        av_frame = av.VideoFrame.from_image(pil_image)  # type: ignore[attr-defined]
        av_frame.pts = frame_num
        if stream.time_base is not None:
            av_frame.time_base = stream.time_base

        # Encode and mux the frame
        for packet in stream.encode(av_frame):  # type: ignore[attr-defined]
            output_container.mux(packet)

    # Flush the encoder
    for packet in stream.encode():  # type: ignore[attr-defined]
        output_container.mux(packet)

    # Close the container
    output_container.close()

    return output_path


def test__configure_stream_threading__with_explicit_thread_count() -> None:
    """Test configuring threading with explicit thread count."""
    video_stream = MagicMock()

    _configure_stream_threading(video_stream=video_stream, num_decode_threads=4)

    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 4


def test__configure_stream_threading__auto_calculate_threads(mocker: MockerFixture) -> None:
    """Test automatic thread count calculation based on CPU count."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=8)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use cpu_count - 1 = 7
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 7


def test__configure_stream_threading__capped_at_16_threads(mocker: MockerFixture) -> None:
    """Test that thread count is capped at 16."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=32)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should be capped at 16
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 16


def test__configure_stream_threading__min_1_thread(mocker: MockerFixture) -> None:
    """Test that at least 1 thread is used even with single CPU."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=1)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use at least 1
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 1
