
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from lightly_studio.models.video import VideoCreate, VideoTable
from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
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
    duration: float = 12.3,
    fps: float = 12.3,

default_sample_video = SampleVideo()

def create_video(
    session: Session,
    dataset_id: UUID,
    video: SampleVideo = default_sample_video,
) -> VideoTable:
    """Helper function to create a sample."""
    return image_resolver.create(
        session=session,
        sample=VideoCreate(
            dataset_id=dataset_id,
            file_path_abs=video.file_path_abs,
            file_name=Path(video.file_path_abs).name,
            width=video.width,
            height=video.height,
            duration=video.duration,
            fps=video.fps
        ),
    )

def create_videos(
    db_session: Session,
    dataset_id: UUID,
    videos: list[SampleVideo],
) -> list[VideoTable]:
    """Creates samples in the database for a given dataset.

    Args:
        db_session: The database session.
        dataset_id: The ID of the dataset to add samples to.
        videos: A list of SampleVideo objects representing the samples to create.

    Returns:
        A list of the created VideoTable objects.
    """
    return [
        create_video(
            session=db_session,
            dataset_id=dataset_id,
            video=video
        )
        for video in videos
    ]
