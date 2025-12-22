"""Tests for collections_resolver - get_root_collections_overview functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionOverviewView, SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_get_root_collections_overview(
    db_session: Session,
) -> None:
    """Test that get_root_collections_overview returns root with correct sample counts."""
    # Create two root collections.
    collection_with_samples = create_collection(
        session=db_session, collection_name="collection_with_samples", sample_type=SampleType.IMAGE
    )
    collection_without_samples = create_collection(
        session=db_session,
        collection_name="collection_without_samples",
        sample_type=SampleType.VIDEO,
    )

    # Add samples to only one collection.
    create_image(
        session=db_session,
        collection_id=collection_with_samples.collection_id,
        file_path_abs="/path/to/image1.jpg",
    )
    create_image(
        session=db_session,
        collection_id=collection_with_samples.collection_id,
        file_path_abs="/path/to/image2.jpg",
    )

    # Call resolver and check result length.
    result = collection_resolver.get_collections_overview(session=db_session)
    assert len(result) == 2

    # Verify collection without samples - this should be first as it was created later.
    ds_without_samples_res = next(
        r for r in result if r.collection_id == collection_without_samples.collection_id
    )
    assert ds_without_samples_res == CollectionOverviewView(
        collection_id=collection_without_samples.collection_id,
        name="collection_without_samples",
        created_at=collection_without_samples.created_at,
        sample_type=SampleType.VIDEO,
        total_sample_count=0,
    )

    # Verify collection with samples
    ds_with_samples_res = next(
        r for r in result if r.collection_id == collection_with_samples.collection_id
    )
    assert ds_with_samples_res == CollectionOverviewView(
        collection_id=collection_with_samples.collection_id,
        name="collection_with_samples",
        created_at=collection_with_samples.created_at,
        sample_type=SampleType.IMAGE,
        total_sample_count=2,
    )
