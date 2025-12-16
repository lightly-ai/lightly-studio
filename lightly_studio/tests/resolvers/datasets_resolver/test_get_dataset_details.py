"""Tests for datasets_resolver - get_dataset_details functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_dataset, create_image


def test_get_dataset_details(
    db_session: Session,
) -> None:
    """Test that get_dataset_details returns correct sample count."""
    dataset = create_dataset(session=db_session, dataset_name="test_dataset")

    create_image(
        session=db_session,
        dataset_id=dataset.collection_id,
        file_path_abs="/path/to/image1.jpg",
    )
    create_image(
        session=db_session,
        dataset_id=dataset.collection_id,
        file_path_abs="/path/to/image2.jpg",
    )
    create_image(
        session=db_session,
        dataset_id=dataset.collection_id,
        file_path_abs="/path/to/image3.jpg",
    )

    result = collection_resolver.get_collection_details(session=db_session, dataset=dataset)

    assert result.collection_id == dataset.collection_id
    assert result.name == dataset.name
    assert result.created_at == dataset.created_at
    assert result.updated_at == dataset.updated_at
    assert result.total_sample_count == 3


def test_get_dataset_details__empty_dataset(
    db_session: Session,
) -> None:
    """Test that get_dataset_details returns zero for empty dataset."""
    dataset = create_dataset(session=db_session, dataset_name="empty_dataset")

    result = collection_resolver.get_collection_details(session=db_session, dataset=dataset)

    assert result.total_sample_count == 0
    assert result.collection_id == dataset.collection_id
    assert result.name == dataset.name
