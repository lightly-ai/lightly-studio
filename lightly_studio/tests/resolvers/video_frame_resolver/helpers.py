from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.video import VideoCreate, VideoFrameCreate, VideoFrameTable, VideoTable
from lightly_studio.resolvers import video_frame_resolver, video_resolver
from lightly_studio.type_definitions import PathLike


@dataclass
class SampleVideo:
    """Helper class to represent a sample video for testing.

    Attributes:
        path: Location of the video file.
        width: Width of the video in pixels.
        height: Height of the video in pixels.
        duration: Duration of the video in seconds.
        fps: Frame rate of the video.

    """

    file_path_abs: PathLike = "/path/to/video.mp4"
    width: int = 640
    height: int = 480
    duration: float = 1.0
    fps: float = 2.0


default_sample_video = SampleVideo()


def create_video_with_frames(
    session: Session,
    dataset_id: UUID,
    video: SampleVideo = default_sample_video,
    invert_frame_sorting: bool = False,
) -> tuple[VideoTable, list[VideoFrameTable]]:
    """Helper function to create a sample."""
    video_sample = video_resolver.create(
        session=session,
        dataset_id=dataset_id,
        sample=VideoCreate(
            file_path_abs=video.file_path_abs,
            file_name=Path(video.file_path_abs).name,
            width=video.width,
            height=video.height,
            duration=video.duration,
            fps=video.fps,
        ),
    )

    n_frames = int(video.duration * video.fps)
    frames_iter = range(n_frames - 1, -1, -1) if invert_frame_sorting else range(n_frames)

    frame_samples = video_frame_resolver.create_many(
        session=session,
        dataset_id=dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=i,
                frame_timestamp=i // video.fps,
                video_sample_id=video_sample.sample_id,
            )
            for i in frames_iter
        ],
    )

    return video_sample, frame_samples
