import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoFrameCreate
from lightly_studio.resolvers import (
    dataset_resolver,
    video_frame_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_resolver.helpers import VideoStub, create_videos


def test_create_many(test_db: Session) -> None:
    """Test bulk creation of video frame samples."""
    dataset_id = create_dataset(session=test_db, sample_type=SampleType.VIDEO).dataset_id

    # Create video.
    sample_video_id = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/video.mp4"),
        ],
    )[0]

    # Create video frames.
    frames_to_create = [
        VideoFrameCreate(
            frame_number=1,
            frame_timestamp_s=0.1,
            frame_timestamp_pts=1,
            parent_sample_id=sample_video_id,
        ),
        VideoFrameCreate(
            frame_number=2,
            frame_timestamp_s=0.2,
            frame_timestamp_pts=2,
            parent_sample_id=sample_video_id,
        ),
    ]

    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=test_db, dataset_id=dataset_id
    )
    created_video_frame_sample_ids = video_frame_resolver.create_many(
        session=test_db, dataset_id=video_frames_dataset_id, samples=frames_to_create
    )

    assert len(created_video_frame_sample_ids) == 2

    retrieved_video_frames = video_frame_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=video_frames_dataset_id,
        sample_ids=created_video_frame_sample_ids,
    )

    # Check if all samples are in the database
    assert len(retrieved_video_frames.samples) == 2
    assert retrieved_video_frames.samples[0].frame_number == 1
    assert retrieved_video_frames.samples[0].frame_timestamp_s == pytest.approx(0.1)
    assert retrieved_video_frames.samples[0].frame_timestamp_pts == 1
    assert retrieved_video_frames.samples[0].parent_sample_id == sample_video_id
    assert retrieved_video_frames.samples[1].frame_number == 2
    assert retrieved_video_frames.samples[1].frame_timestamp_s == pytest.approx(0.2)
    assert retrieved_video_frames.samples[1].frame_timestamp_pts == 2
    assert retrieved_video_frames.samples[1].parent_sample_id == sample_video_id
