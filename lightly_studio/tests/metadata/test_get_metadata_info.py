"""Test metadata info resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    get_all_metadata_keys_and_schema,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_get_all_metadata_keys_and_schema__with_numerical_values(
    test_db: Session,
) -> None:
    """Test getting metadata keys and schema with min/max values for numerical types."""
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id

    # Create samples with different metadata
    sample1 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    ).sample
    sample3 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample3.png",
    ).sample

    # Add metadata with different types.
    sample1["temperature"] = 25.5
    sample1["count"] = 10
    sample1["location"] = "city"

    sample2["temperature"] = 15.2
    sample2["count"] = 5
    sample2["location"] = "mountain"

    sample3["temperature"] = 30.0
    sample3["count"] = 20
    sample3["is_processed"] = True

    # Get metadata info
    result = get_all_metadata_keys_and_schema(session=test_db, collection_id=dataset_id)

    # Verify the result structure.
    assert len(result) == 4  # temperature, count, location, is_processed

    # Find each metadata key.
    temperature_info = next(item for item in result if item.name == "temperature")
    count_info = next(item for item in result if item.name == "count")
    location_info = next(item for item in result if item.name == "location")
    is_processed_info = next(item for item in result if item.name == "is_processed")

    # Check temperature (float type with min/max).
    assert temperature_info.type == "float"
    assert temperature_info.min == pytest.approx(15.2)
    assert temperature_info.max == pytest.approx(30.0)

    # Check count (integer type with min/max).
    assert count_info.type == "integer"
    assert count_info.min == 5
    assert count_info.max == 20

    # Check location (string type without min/max).
    assert location_info.type == "string"
    assert location_info.min is None
    assert location_info.max is None

    # Check is_processed (boolean type without min/max).
    assert is_processed_info.type == "boolean"
    assert is_processed_info.min is None
    assert is_processed_info.max is None


def test_get_all_metadata_keys_and_schema__no_numerical_values(
    test_db: Session,
) -> None:
    """Test getting metadata keys and schema with only non-numerical types."""
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id

    # Create sample with only non-numerical metadata
    sample = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample

    # Add metadata.
    sample["location"] = "city"
    sample["is_processed"] = True
    sample["tags"] = ["tag1", "tag2"]

    # Get metadata info.
    result = get_all_metadata_keys_and_schema(session=test_db, collection_id=dataset_id)

    # Verify the result structure.
    assert len(result) == 3  # location, is_processed, tags

    # Check that no numerical types have min/max values.
    for item in result:
        assert item.min is None
        assert item.max is None


def test_get_all_metadata_keys_and_schema__empty_dataset(
    test_db: Session,
) -> None:
    """Test getting metadata keys and schema for dataset with no metadata."""
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id

    # Create sample without metadata.
    create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    # Get metadata info.
    result = get_all_metadata_keys_and_schema(session=test_db, collection_id=dataset_id)

    # Should return empty list.
    assert result == []
