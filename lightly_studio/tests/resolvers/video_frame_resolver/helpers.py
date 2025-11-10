from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import dataset_resolver, video_frame_resolver, video_resolver
from tests.resolvers.video_resolver.helpers import VideoStub


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

    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=session, dataset_id=dataset_id
    )

    frame_samples = video_frame_resolver.create_many(
        session=session,
        dataset_id=video_frames_dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=i,
                frame_timestamp_s=i / video.fps,
                parent_sample_id=video_sample_id,
            )
            for i in range(n_frames)
        ],
    )

    return VideoWithFrames(video_sample_id=video_sample_id, frame_sample_ids=frame_samples, video_frames_dataset_id=video_frames_dataset_id)
