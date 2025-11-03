from sqlmodel import Session

from lightly_studio.models.video import VideoCreate
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)


def test_create_many_samples(test_db: Session) -> None:
    """Test bulk creation of video samples."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    samples_to_create = [
        VideoCreate(
            file_path_abs=f"/path/to/video_{i}.mp4",
            file_name=f"video_{i}.mp4",
            width=100 + i * 10,
            height=200 + i * 10,
            duration=12.3 + i * 10,
            fps=12.3 + i * 10,
        )
        for i in range(5)
    ]

    created_samples = video_resolver.create_many(
        session=test_db, dataset_id=dataset_id, samples=samples_to_create
    )

    assert len(created_samples) == 5
    # Check if order is preserved
    for i, sample in enumerate(created_samples):
        assert sample.file_name == f"video_{i}.mp4"

    retrieved_samples = video_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 5
    for i, sample in enumerate(retrieved_samples.samples):
        assert sample.file_name == f"video_{i}.mp4"
