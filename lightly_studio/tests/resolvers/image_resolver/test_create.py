import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_dataset


def test_create(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    image = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image.png",
            file_name="image.png",
            width=100,
            height=200,
        ),
    )

    assert image.dataset_id == dataset.dataset_id
    assert image.file_path_abs == "/path/to/image.png"
    assert image.file_name == "image.png"
    assert image.width == 100
    assert image.height == 200

    # Fetch from db
    retrieved_images = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset.dataset_id
    )
    assert len(retrieved_images.samples) == 1
    assert retrieved_images.samples[0].sample_id == image.sample_id


def test_create__sample_type_mismatch(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    with pytest.raises(ValueError, match="is having sample type 'video', expected 'image'"):
        image_resolver.create(
            session=test_db,
            sample=ImageCreate(
                dataset_id=dataset.dataset_id,
                file_path_abs="/path/to/image.png",
                file_name="image.png",
                width=100,
                height=200,
            ),
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


def test_create_many__sample_type_mismatch(test_db: Session) -> None:
    """Test bulk creation of samples."""
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    samples_to_create = [
        ImageCreate(
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="sample1.png",
            width=100,
            height=200,
        ),
        ImageCreate(
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="sample2.png",
            width=100,
            height=200,
        ),
    ]
    with pytest.raises(ValueError, match="is having sample type 'video', expected 'image'"):
        image_resolver.create_many(session=test_db, samples=samples_to_create)
