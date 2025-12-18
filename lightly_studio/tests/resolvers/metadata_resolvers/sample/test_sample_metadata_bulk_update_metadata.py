"""Test metadata resolver bulk set metadata."""

from sqlmodel import Session, select

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.resolvers import (
    metadata_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_bulk_update_metadata(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    # Create samples.
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
    # Prepare metadata for all samples
    sample_metadata = []
    sample_metadata.append(
        (
            sample1.sample_id,
            {
                "temperature": 25,
                "location": "city",
            },
        )
    )
    sample_metadata.append(
        (
            sample2.sample_id,
            {
                "temperature": 30,
                "location": "rural",
            },
        )
    )

    # Bulk insert metadata
    metadata_resolver.bulk_update_metadata(test_db, sample_metadata)

    assert sample1["location"] == "city"
    assert sample2["location"] == "rural"


def test_bulk_update_metadata__existing_metadata(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    # Create samples.
    sample = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    # Prepare metadata for all samples
    sample_metadata = [
        (
            sample.sample_id,
            {
                "location": "city",
            },
        )
    ]

    # Bulk insert metadata
    metadata_resolver.bulk_update_metadata(test_db, sample_metadata)

    assert sample["location"] == "city"

    # Test updating existing metadata.
    sample_metadata_update = [
        (
            sample.sample_id,
            {
                "temperature": 25,
            },
        ),
    ]

    # Bulk update metadata.
    metadata_resolver.bulk_update_metadata(test_db, sample_metadata_update)

    # Verify old keys still exist.
    assert sample["location"] == "city"

    # Verify new keys were added.
    assert sample["temperature"] == 25

    # Verify no duplicate rows were created (should only be 1 metadata row per sample).
    metadata_count_sample = len(
        test_db.exec(
            select(SampleMetadataTable).where(SampleMetadataTable.sample_id == sample.sample_id)
        ).all()
    )
    assert metadata_count_sample == 1


def test_bulk_update_metadata__overwrite_existing_metadata(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    # Create samples.
    sample = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    # Prepare metadata for all samples
    sample_metadata = [
        (
            sample.sample_id,
            {
                "temperature": 25,
            },
        ),
    ]

    # Bulk insert metadata
    metadata_resolver.bulk_update_metadata(test_db, sample_metadata)

    assert sample["temperature"] == 25

    # Test updating existing metadata.
    sample_metadata_update = [
        (
            sample.sample_id,
            {
                "temperature": 15,
            },
        ),
    ]

    # Bulk update metadata.
    metadata_resolver.bulk_update_metadata(test_db, sample_metadata_update)

    # Verify metadata was overwritten.
    assert sample["temperature"] == 15

    # Verify no duplicate rows were created (should only be 1 metadata row per sample).
    metadata_count_sample1 = len(
        test_db.exec(
            select(SampleMetadataTable).where(SampleMetadataTable.sample_id == sample.sample_id)
        ).all()
    )
    assert metadata_count_sample1 == 1
