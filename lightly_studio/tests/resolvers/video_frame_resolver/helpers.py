from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import video_frame_resolver, video_resolver
from tests.resolvers.video_resolver.helpers import VideoStub


def create_video_with_frames(
    session: Session,
    dataset_id: UUID,
    video: VideoStub,
    invert_frame_sorting: bool = False,
) -> tuple[UUID, list[UUID]]:
    """Helper function to create a sample."""
    video_sample_ids = video_resolver.create_many(
        session=session,
        dataset_id=dataset_id,
        samples=[
            VideoCreate(
                file_path_abs=video.path,
                file_name=Path(video.path).name,
                width=video.width,
                height=video.height,
                duration=video.duration,
                fps=video.fps,
            )
        ],
    )
    assert len(video_sample_ids) == 1
    n_frames = int(video.duration * video.fps)
    frames_iter = range(n_frames - 1, -1, -1) if invert_frame_sorting else range(n_frames)

    frame_samples = video_frame_resolver.create_many(
        session=session,
        dataset_id=dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=i,
                frame_timestamp=i // video.fps,
                video_sample_id=video_sample_ids[0],
            )
            for i in frames_iter
        ],
    )

    return video_sample_ids[0], frame_samples
