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


class TestCreateMany:
    def test_create_many(self, test_db: Session) -> None:
        """Test bulk creation of video samples."""
        dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
        dataset_id = dataset.dataset_id

        samples_to_create = [
            VideoCreate(
                file_path_abs=f"/path/to/video_{i}.mp4",
                file_name=f"video_{i}.mp4",
                width=100 + i * 10,
                height=200 + i * 10,
                duration=12.3 + i * 10,
                fps=30 + i * 10,
            )
            for i in range(5)
        ]

        created_samples_ids = video_resolver.create_many(
            session=test_db, dataset_id=dataset_id, samples=samples_to_create
        )

        retrieved_samples = video_resolver.get_all_by_dataset_id(
            session=test_db, dataset_id=dataset_id, sample_ids=created_samples_ids
        )

        # Check if all samples are really in the database
        assert len(retrieved_samples.samples) == 5
        for i, sample in enumerate(retrieved_samples.samples):
            assert sample.file_name == f"video_{i}.mp4"

    def test_create_many__sample_type_missmatch(self, test_db: Session) -> None:
        """Test creation of video samples with mismatched sample type."""
        dataset = create_dataset(session=test_db)
        dataset_id = dataset.dataset_id

        samples_to_create = [
            VideoCreate(
                file_path_abs=f"/path/to/video_{i}.mp4",
                file_name=f"video_{i}.mp4",
                width=100 + i * 10,
                height=200 + i * 10,
                duration=12.3 + i * 10,
                fps=30.0 + i * 10,
            )
            for i in range(5)
        ]

        with pytest.raises(ValueError, match="is having sample type 'image', expected 'video'"):
            video_resolver.create_many(
                session=test_db, dataset_id=dataset_id, samples=samples_to_create
            )
