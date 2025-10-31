from sqlmodel import Session

from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)


def test_create_many_samples(test_db: Session) -> None:
    """Test bulk creation of samples."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    samples_to_create = [
        ImageCreate(
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/batch_sample_{i}.png",
            file_name=f"batch_sample_{i}.png",
            width=100 + i * 10,
            height=200 + i * 10,
        )
        for i in range(5)
    ]

    created_samples = image_resolver.create_many(session=test_db, samples=samples_to_create)

    assert len(created_samples) == 5
    # Check if order is preserved
    for i, sample in enumerate(created_samples):
        assert sample.file_name == f"batch_sample_{i}.png"

    retrieved_samples = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 5
    for i, sample in enumerate(retrieved_samples.samples):
        assert sample.file_name == f"batch_sample_{i}.png"
