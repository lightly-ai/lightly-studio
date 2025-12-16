from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate, VideoTable
from lightly_studio.resolvers import (
    collection_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.type_definitions import PathLike


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


def create_video(session: Session, dataset_id: UUID, video: VideoStub) -> VideoTable:
    sample_ids = video_resolver.create_many(
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
        ],
    )
    video_table = video_resolver.get_by_id(session=session, sample_id=sample_ids[0])
    assert video_table is not None
    return video_table


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


@dataclass
class VideoWithFrames:
    video_sample_id: UUID
    frame_sample_ids: list[UUID]
    video_frames_dataset_id: UUID


def create_video_with_frames(
    session: Session,
    dataset_id: UUID,
    video: VideoStub,
) -> VideoWithFrames:
    """Create a video sample with associated frame samples.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        video: The video stub containing video metadata.

    Number of frames are calculated using the video's duration and fps.

    Returns:
        The video sample id and list of frame sample ids in a VideoWithFrames object.
    """
    video_sample_id = video_resolver.create_many(
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
        ],
    )[0]
    n_frames = int(video.duration_s * video.fps)

    video_frames_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=session, dataset_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )

    frame_samples = video_frame_resolver.create_many(
        session=session,
        dataset_id=video_frames_dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=i,
                frame_timestamp_s=i / video.fps,
                frame_timestamp_pts=i,
                parent_sample_id=video_sample_id,
            )
            for i in range(n_frames)
        ],
    )

    return VideoWithFrames(
        video_sample_id=video_sample_id,
        frame_sample_ids=frame_samples,
        video_frames_dataset_id=video_frames_dataset_id,
    )
