"""Tests for datasets_resolver - get_root_datasets_overview functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionOverviewView, SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_dataset, create_image


def test_get_root_datasets_overview(
    db_session: Session,
) -> None:
    """Test that get_root_datasets_overview returns root datasets with correct sample counts."""
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
        dataset_id=dataset_with_samples.collection_id,
        file_path_abs="/path/to/image1.jpg",
    )
    create_image(
        session=db_session,
        dataset_id=dataset_with_samples.collection_id,
        file_path_abs="/path/to/image2.jpg",
    )

    # Call resolver and check result length.
    result = collection_resolver.get_datasets_overview(session=db_session)
    assert len(result) == 2

    # Verify dataset without samples - this should be first as it was created later.
    ds_without_samples_res = next(
        r for r in result if r.collection_id == dataset_without_samples.collection_id
    )
    assert ds_without_samples_res == CollectionOverviewView(
        collection_id=dataset_without_samples.collection_id,
        name="dataset_without_samples",
        created_at=dataset_without_samples.created_at,
        sample_type=SampleType.VIDEO,
        total_sample_count=0,
    )

    # Verify dataset with samples
    ds_with_samples_res = next(
        r for r in result if r.collection_id == dataset_with_samples.collection_id
    )
    assert ds_with_samples_res == CollectionOverviewView(
        collection_id=dataset_with_samples.collection_id,
        name="dataset_with_samples",
        created_at=dataset_with_samples.created_at,
        sample_type=SampleType.IMAGE,
        total_sample_count=2,
    )
