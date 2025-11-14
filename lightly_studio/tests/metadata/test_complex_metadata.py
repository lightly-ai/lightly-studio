"""Test metadata resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import (
    metadata_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.metadata_resolver.metadata_filter import (
    Metadata,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_dataset,
    create_image,
)


def test_complex_metadata(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    # Add metadata
    sample["temperature"] = 25
    sample["location"] = "city"
    sample["gps_location"] = GPSCoordinate(lat=40.7128, lon=-74.0060)

    assert isinstance(sample["gps_location"], GPSCoordinate)
    assert sample["gps_location"].lat == 40.7128
    assert sample["gps_location"].lon == -74.0060

    metadata_resolver.set_value_for_sample(
        session=test_db,
        sample_id=sample.sample_id,
        key="gps_location",
        value=GPSCoordinate(lat=50.7128, lon=-54.0060),
    )
    assert sample["gps_location"].lat == 50.7128
    assert sample["gps_location"].lon == -54.0060


def test_complex_metadata_update_type(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    # Add metadata
    sample["gps_location"] = GPSCoordinate(lat=40.7128, lon=-74.0060)

    assert isinstance(sample["gps_location"], GPSCoordinate)
    # Try to set a value of a different type.
    with pytest.raises(
        ValueError,
        match="Value type mismatch for key 'gps_location'. Expected gps_coordinate, got integer",
    ):
        sample["gps_location"] = 12


def test_complex_metadata_filter(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    ).sample

    # Add metadata
    sample1["temperature"] = 25
    sample1["location"] = "city"
    sample1["gps_location"] = GPSCoordinate(lat=40.7128, lon=-74.0060)
    sample2["temperature"] = 15
    sample2["location"] = "desert"
    sample2["gps_location"] = GPSCoordinate(lat=34.0522, lon=-118.2437)

    gps_filter = [Metadata("gps_location.lat") > 35]
    sample_filter = SampleFilter(metadata_filters=gps_filter)
    samples = sample_resolver.get_filtered_samples(session=test_db, filters=sample_filter).samples
    assert len(samples) == 1
    assert samples[0].sample_id == sample1.sample_id
