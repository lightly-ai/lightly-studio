from sqlmodel import Session

from lightly_studio.models.video import VideoFrameCreate
from lightly_studio.resolvers import (
    video_frame_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_resolver.helpers import create_video


def test_create(test_db: Session) -> None:
    """Test creation of video."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create video
    sample = create_video(session=test_db, dataset_id=dataset_id)

    # Create VideoFrames
    frame_to_create = VideoFrameCreate(
        frame_number=101,
        frame_timestamp=101,
        video_sample_id=sample.sample_id,
    )

    sample_frame = video_frame_resolver.create(
        session=test_db, dataset_id=dataset_id, sample=frame_to_create
    )

    assert sample_frame.video_sample_id == sample.sample_id
    assert sample_frame.frame_number == 101
    assert sample_frame.frame_timestamp == 101

    retrieved_samples = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id
    )

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 1
    assert retrieved_samples.samples[0].frame_number == 101


def test_create_many_samples(test_db: Session) -> None:
    """Test bulk creation of video samples."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create video
    sample_video = create_video(session=test_db, dataset_id=dataset_id)

    frames_to_create = [
        VideoFrameCreate(
            frame_number=i,
            frame_timestamp=i * 10,
            video_sample_id=sample_video.sample_id,
        )
        for i in range(5)
    ]

    created_samples = video_frame_resolver.create_many(
        session=test_db, dataset_id=dataset_id, samples=frames_to_create
    )

    assert len(created_samples) == 5
    # Check if order is preserved
    for i, sample in enumerate(created_samples):
        assert sample.frame_number == i
        assert sample.video_sample_id == sample_video.sample_id

    retrieved_samples = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id
    )

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 5
    for i, sample in enumerate(retrieved_samples.samples):
        assert sample.frame_number == i
        assert sample.video_sample_id == sample_video.sample_id
