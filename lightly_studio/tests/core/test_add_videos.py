from pathlib import Path

import av
import numpy as np
from PIL import Image as PILImage
from sqlmodel import Session

from lightly_studio.core import add_videos
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    video_frame_resolver,
    video_resolver,
)
from tests.helpers_resolvers import create_dataset


def test_load_into_dataset_from_paths(db_session: Session, tmp_path: Path) -> None:
    dataset = create_dataset(db_session, sample_type=SampleType.VIDEO)
    # Create two temporary video files
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
    # Act
    frame_sample_ids = add_videos.load_into_dataset_from_paths(
        session=db_session,
        dataset_id=dataset.dataset_id,
        video_paths=[str(first_video_path), str(second_video_path)],
        fps=2.0,
    )
    assert len(frame_sample_ids) == 60  # Should return 60 frame sample IDs

    # Assert - Check video sample was created
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

    # Assert - Check video frames were created
    video_frames = video_frame_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=dataset.dataset_id,
    ).samples
    assert len(video_frames) == 60  # Should have 60 frames


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
