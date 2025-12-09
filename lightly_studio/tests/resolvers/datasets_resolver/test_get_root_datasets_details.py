"""Tests for datasets_resolver - get_root_datasets_details functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import dataset_resolver
from tests.helpers_resolvers import create_dataset, create_image


def test_get_root_datasets_details(
    db_session: Session,
) -> None:
    """Test that get_root_datasets_details returns root datasets with correct sample counts."""
    # Create two root datasets.
    dataset_with_samples = create_dataset(
        session=db_session, dataset_name="dataset_with_samples", sample_type=SampleType.IMAGE
    )
    dataset_without_samples = create_dataset(
        session=db_session,
        dataset_name="dataset_without_samples",
        sample_type=SampleType.VIDEO,
    )

    # Add samples to only one dataset.
    create_image(
        session=db_session,
        dataset_id=dataset_with_samples.dataset_id,
        file_path_abs="/path/to/image1.jpg",
    )
    create_image(
        session=db_session,
        dataset_id=dataset_with_samples.dataset_id,
        file_path_abs="/path/to/image2.jpg",
    )

    # Call resolver and check result length.
    result = dataset_resolver.get_root_datasets_details(session=db_session)
    assert len(result) == 2

    # Verify dataset with samples
    ds_with_samples_res = next(r for r in result if r.dataset_id == dataset_with_samples.dataset_id)
    assert ds_with_samples_res.total_sample_count == 2
    assert ds_with_samples_res.name == "dataset_with_samples"
    assert ds_with_samples_res.sample_type == SampleType.IMAGE
    assert ds_with_samples_res.dir_path_abs == "/path/to/dataset" # TODO (Mihnea 12/25): replace this with the actual location
    assert ds_with_samples_res.created_at == dataset_with_samples.created_at

    # Verify dataset without samples
    ds_without_samples_res = next(
        r for r in result if r.dataset_id == dataset_without_samples.dataset_id
    )
    assert ds_without_samples_res.total_sample_count == 0
    assert ds_without_samples_res.name == "dataset_without_samples"
    assert ds_without_samples_res.sample_type == SampleType.VIDEO
    assert ds_without_samples_res.dir_path_abs == "/path/to/dataset" # TODO (Mihnea 12/25): replace this with the actual location
    assert ds_without_samples_res.created_at == dataset_without_samples.created_at
