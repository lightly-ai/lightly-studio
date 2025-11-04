import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_dataset


def test_create_many_samples(test_db: Session) -> None:
    """Test bulk creation of samples."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Use out of order file names to verify that order is preserved
    samples_to_create = [
        ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/image_1.png",
            file_name="image_1.png",
            width=100,
            height=200,
        ),
        ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/image_0.png",
            file_name="image_0.png",
            width=300,
            height=400,
        ),
    ]

    created_sample_ids = image_resolver.create_many(session=test_db, samples=samples_to_create)
    retrieved_samples = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=created_sample_ids
    ).samples

    # Retrieved samples are ordered by path
    assert len(retrieved_samples) == 2
    assert retrieved_samples[0].file_name == "image_0.png"
    assert retrieved_samples[1].file_name == "image_1.png"

    # Created_sample_ids should preserve the order of input samples
    assert len(created_sample_ids) == 2
    assert created_sample_ids[0] == retrieved_samples[1].sample_id
    assert created_sample_ids[1] == retrieved_samples[0].sample_id

    # Check other fields
    assert retrieved_samples[0].dataset_id == dataset_id
    assert retrieved_samples[0].file_path_abs == "/path/to/image_0.png"
    assert retrieved_samples[0].file_name == "image_0.png"
    assert retrieved_samples[0].width == 300
    assert retrieved_samples[0].height == 400


def test_create_many__sample_type_mismatch(test_db: Session) -> None:
    """Test bulk creation of samples."""
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    with pytest.raises(ValueError, match="is having sample type 'video', expected 'image'"):
        image_resolver.create_many(
            session=test_db,
            samples=[
                ImageCreate(
                    dataset_id=dataset.dataset_id,
                    file_path_abs="/path/to/sample1.png",
                    file_name="sample1.png",
                    width=100,
                    height=200,
                ),
            ],
        )
