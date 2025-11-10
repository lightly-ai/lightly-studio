from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoCreate, VideoTable
from lightly_studio.resolvers import (
    video_resolver,
)
from lightly_studio.type_definitions import PathLike
from tests.helpers_resolvers import create_dataset


@dataclass
class VideoStub:
    """Helper class to represent a sample video for testing.

    Attributes:
        path: Location of the video file.
        width: Width of the video in pixels.
        height: Height of the video in pixels.
        duration: Duration of the video in seconds.
        fps: Frame rate of the video.

    """

    path: PathLike = "/path/to/video.mp4"
    width: int = 640
    height: int = 480
    duration_s: float = 12.3
    fps: float = 30.0


def create_videos(
    session: Session,
    dataset_id: UUID,
    videos: list[VideoStub],
) -> list[UUID]:
    """Creates samples in the database for a given dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to add samples to.
        videos: A list of SampleVideo objects representing the samples to create.

    Returns:
        A list of the created VideoTable objects IDs.
    """
    return video_resolver.create_many(
        session=session,
        dataset_id=dataset_id,
        samples=[
            VideoCreate(
                file_path_abs=video.path,
                file_name=Path(video.path).name,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
            )
            for video in videos
        ],
    )


def create_videos_to_fake_dataset(
    db_session: Session,
) -> list[VideoTable]:
    """Create test videos for a given dataset."""
    dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=db_session,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    return list(video_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=dataset_id,
    ).samples)
