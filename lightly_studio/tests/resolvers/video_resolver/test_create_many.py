import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoCreate
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)


def test_create_many(test_db: Session) -> None:
    """Test bulk creation of video samples."""
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    samples_to_create = [
        VideoCreate(
            file_path_abs="/path/to/video_0.mp4",
            file_name="video_0.mp4",
            width=100,
            height=200,
            duration_s=12.3,
            fps=30.0,
        ),
        VideoCreate(
            file_path_abs="/path/to/video_1.mp4",
            file_name="video_1.mp4",
            width=101,
            height=201,
            duration_s=22.3,
            fps=30.0,
        ),
    ]

    created_samples_ids = video_resolver.create_many(
        session=test_db, dataset_id=dataset_id, samples=samples_to_create
    )

    retrieved_samples = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=created_samples_ids
    )

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 2
    assert retrieved_samples.samples[0].file_name == "video_0.mp4"
    assert retrieved_samples.samples[0].width == 100
    assert retrieved_samples.samples[0].height == 200
    assert retrieved_samples.samples[0].duration_s == pytest.approx(12.3)
    assert retrieved_samples.samples[0].fps == pytest.approx(30.0)

    assert retrieved_samples.samples[1].file_name == "video_1.mp4"


def test_create_many__sample_type_mismatch(test_db: Session) -> None:
    """Test creation of video samples with mismatched sample type."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    with pytest.raises(ValueError, match="is having sample type 'image', expected 'video'"):
        video_resolver.create_many(
            session=test_db,
            dataset_id=dataset_id,
            samples=[
                VideoCreate(
                    file_path_abs="/path/to/video_0.mp4",
                    file_name="video_0.mp4",
                    width=100,
                    height=200,
                    duration_s=12.3,
                    fps=30.0,
                )
            ],
        )
