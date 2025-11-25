"""Example script demonstrating metadata capabilities.

This script shows how to:
1. Load an existing dataset using DatasetLoader
2. Add metadata to all samples using bulk operations
3. Add metadata to individual samples
4. Filter samples using various metadata types
"""

from __future__ import annotations

import logging
import random
import time
from uuid import UUID

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.sample import Sample
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import Metadata
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

logger = logging.getLogger(__name__)

# Environment variables
env = Env()
env.read_env()
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")


def load_existing_dataset() -> tuple[ls.Dataset, list[Sample]]:
    """Load an existing dataset using DatasetLoader.

    Returns:
        Tuple of (dataset, samples).
    """
    logger.info(" Loading existing dataset...")

    dataset = ls.Dataset.create()
    dataset.add_samples_from_path(path=dataset_path)

    # Get all samples from the dataset
    samples = dataset.query().to_list()

    logger.info("✅ Loaded dataset with %s samples", len(samples))
    return dataset, samples


def add_bulk_metadata(session: Session, sample_ids: list[UUID]) -> None:
    """Add metadata to all samples using bulk operations."""
    logger.info("\n Adding bulk metadata to all samples...")

    # Prepare bulk metadata with random values
    sample_metadata = []
    for sample_id in sample_ids:
        # Generate random metadata
        temp = random.randint(10, 40)
        loc = random.choice(["city", "rural", "mountain", "coastal", "desert"])
        lat = random.uniform(-90.0, 90.0)
        lon = random.uniform(-180.0, 180.0)
        gps_coord = GPSCoordinate(lat=lat, lon=lon)
        confidence = random.uniform(0.5, 1.0)
        is_processed = random.choice([True, False])

        sample_metadata.append(
            (
                sample_id,
                {
                    "temperature": temp,
                    "location": loc,
                    "gps_coordinates": gps_coord,
                    "confidence": confidence,
                    "is_processed": is_processed,
                    "batch_id": "bulk_001",  # Mark as bulk-added
                },
            )
        )

    # Bulk insert metadata
    start_time = time.time()
    metadata_resolver.bulk_update_metadata(session, sample_metadata)
    elapsed_time = time.time() - start_time

    logger.info("✅ Added metadata to %s samples in %.2fs", len(sample_ids), elapsed_time)


def add_individual_metadata(samples: list[Sample]) -> None:
    """Add metadata to individual samples."""
    logger.info("\n Adding individual metadata to specific samples...")

    # Add metadata to first 5 samples individually
    for i, sample in enumerate(samples[:5]):
        logger.info(" Adding metadata to sample %s %s...", sample.file_name, sample.sample_id)
        # Add some specific metadata
        sample.metadata["special_metadata"] = f"sample_{i + 1}_special"
        sample.metadata["priority"] = random.randint(1, 10)
        sample.metadata["list"] = [1, 2, 3]
        sample.metadata["custom_gps"] = GPSCoordinate(
            lat=40.7128 + i * 0.1,  # Slightly different coordinates
            lon=-74.0060 + i * 0.1,
        )

    logger.info("✅ Added individual metadata to %s samples", min(5, len(samples)))


def demonstrate_bulk_metadata_filters(dataset: ls.Dataset) -> None:
    """Demonstrate filtering with bulk-added metadata."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    # `dataset._inner` when implemented.
    dataset_table = dataset._inner  # noqa: SLF001

    logger.info("\n Bulk Metadata Filters:")
    logger.info("=" * 50)

    # Filter by temperature
    logger.info("\n1. Filter by temperature > 25:")
    filter_temp = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("temperature") > 25])  # noqa PLR2004
    )
    images = dataset_table.get_samples(filters=filter_temp)
    logger.info("   Found %s samples with temperature > 25", len(images))
    for image in images[:3]:  # Show first 3
        logger.info(" %s: %s", image.file_name, image.sample["temperature"])

    # Filter by location
    logger.info("\n2. Filter by location == 'city':")
    filter_location = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("location") == "city"])
    )
    images = dataset_table.get_samples(filters=filter_location)
    logger.info("   Found %s samples from cities", len(images))
    for image in images[:3]:  # Show first 3
        logger.info(" %s: %s", image.file_name, image.sample["location"])

    # Filter by GPS coordinates
    logger.info("\n3. Filter by latitude > 0° (Northern hemisphere):")
    filter_lat = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("gps_coordinates.lat") > 0])
    )
    images = dataset_table.get_samples(filters=filter_lat)
    logger.info("   Found %s samples in Northern hemisphere", len(images))
    for image in images[:3]:  # Show first 3
        gps = image.sample["gps_coordinates"]
        logger.info(" %s: lat=%.4f, lon=%.4f", image.file_name, gps.lat, gps.lon)

    # Filter by confidence
    logger.info("\n4. Filter by high confidence (> 0.9):")
    filter_confidence = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("confidence") > 0.9]  # noqa PLR2004
        )
    )
    images = dataset_table.get_samples(filters=filter_confidence)
    logger.info("   Found %s samples with confidence > 0.9", len(images))
    for image in images[:3]:  # Show first 3
        logger.info("   📸 %s: confidence=%.3f", image.file_name, image.sample["confidence"])


def demonstrate_individual_metadata_filters(dataset: ls.Dataset) -> None:
    """Demonstrate filtering with individually-added metadata."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    # `dataset._inner` when implemented.
    dataset_table = dataset._inner  # noqa: SLF001

    logger.info("\n Individual Metadata Filters:")
    logger.info("=" * 50)

    # Filter by special metadata
    logger.info("\n1. Filter by special metadata (individually added):")
    filter_special = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("special_metadata") == "sample_1_special"]
        )
    )
    images = dataset_table.get_samples(filters=filter_special)
    logger.info("   Found %s samples with special metadata", len(images))
    for image in images:
        logger.info(" %s: %s", image.file_name, image.sample["special_metadata"])

    # Filter by priority
    logger.info("\n2. Filter by high priority (> 7):")
    filter_priority = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("priority") > 7])  # noqa PLR2004
    )
    images = dataset_table.get_samples(filters=filter_priority)
    logger.info("   Found %s samples with priority > 7", len(images))
    for image in images:
        logger.info(" %s: priority=%s", image.file_name, image.sample["priority"])

    # Filter by custom GPS
    logger.info("\n3. Filter by custom GPS coordinates:")
    filter_custom_gps = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("custom_gps.lat") > 40.8]  # noqa PLR2004
        )
    )
    images = dataset_table.get_samples(filters=filter_custom_gps)
    logger.info("   Found %s samples with custom GPS lat > 40.8", len(images))
    for image in images:
        gps = image.sample["custom_gps"]
        logger.info(" %s: lat=%.4f, lon=%.4f", image.file_name, gps.lat, gps.lon)


def demonstrate_combined_filters(dataset: ls.Dataset) -> None:
    """Demonstrate combining multiple filters."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    # `dataset._inner` when implemented.
    dataset_table = dataset._inner  # noqa: SLF001

    logger.info("\n Combined Filters:")
    logger.info("=" * 50)

    # Multiple conditions
    logger.info("\n1. Find high-confidence, processed, warm images:")
    filter_combined = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                Metadata("confidence") > 0.8,  # noqa PLR2004
                Metadata("is_processed") == True,  # noqa E712
                Metadata("temperature") > 25,  # noqa PLR2004
            ]
        )
    )
    images = dataset_table.get_samples(filters=filter_combined)
    logger.info("   Found %s samples matching all criteria", len(images))
    for image in images[:3]:
        logger.info(
            " %s: conf=%.2f, temp=%s, processed=%s",
            image.file_name,
            image.sample["confidence"],
            image.sample["temperature"],
            image.sample["is_processed"],
        )

    # Complex GPS + other filters
    logger.info("\n2. Find northern hemisphere, high-confidence images:")
    filter_gps_combined = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                Metadata("gps_coordinates.lat") > 0,  # Northern hemisphere
                Metadata("confidence") > 0.85,  # noqa PLR2004
                Metadata("location") == "city",
            ]
        )
    )
    images = dataset_table.get_samples(filters=filter_gps_combined)
    logger.info(
        "   Found %s samples in northern hemisphere cities with high confidence", len(images)
    )
    for image in images[:3]:
        gps = image.sample["gps_coordinates"]
        logger.info(
            " %s: lat=%.4f, conf=%.2f",
            image.file_name,
            gps.lat,
            image.sample["confidence"],
        )


def demonstrate_dictionary_like_access(samples: list[Sample]) -> None:
    """Demonstrate adding metadata using dictionary-like access."""
    logger.info("\n Dictionary-like Metadata Access:")
    logger.info("=" * 50)

    # Get the first few samples to demonstrate
    samples = samples[:2]

    logger.info("\n1. Adding metadata using sample.metadata['key'] = value syntax:")

    # Add different types of metadata to different samples
    samples[0].metadata["temperature"] = 25
    samples[0].metadata["location"] = "city"
    samples[0].metadata["is_processed"] = True
    samples[0].metadata["confidence"] = 0.95
    logger.info(
        " %s: temp=%s°C, location=%s, processed=%s",
        samples[0].file_name,
        samples[0].metadata["temperature"],
        samples[0].metadata["location"],
        samples[0].metadata["is_processed"],
    )

    samples[1].metadata["temperature"] = 15
    samples[1].metadata["location"] = "mountain"
    samples[1].metadata["gps_coordinates"] = GPSCoordinate(lat=40.7128, lon=-74.0060)
    samples[1].metadata["tags"] = ["outdoor", "nature", "landscape"]
    logger.info(
        " %s: temp=%s°C, location=%s, tags=%s",
        samples[1].file_name,
        samples[1].metadata["temperature"],
        samples[1].metadata["location"],
        samples[1].metadata["tags"],
    )

    # Demonstrate reading metadata
    logger.info("\n2. Reading metadata using sample.metadata['key'] syntax:")
    for sample in samples:
        logger.info(" %s:", sample.file_name)
        logger.info("      Temperature: %s°C", sample.metadata["temperature"])
        logger.info("      Location: %s", sample.metadata["location"])
        gps = sample.metadata["gps_coordinates"]
        logger.info("      GPS: lat=%.4f, lon=%.4f", gps.lat, gps.lon)
        logger.info("      Tags: %s", sample.metadata["tags"])

    # Demonstrate None return for missing keys
    logger.info("  Note: sample.metadata['key'] returns None for missing keys")
    missing_value = samples[0].metadata["nonexistent_key"]
    if missing_value is None:
        logger.info(" sample.metadata['nonexistent_key']: %s", missing_value)

    logger.info("✅ Added metadata to %s samples using dictionary-like access", len(samples))

    # Demonstrate schema presentation
    try:
        samples[0].metadata["temperature"] = "string_value"  # Invalid type for demonstration
        logger.info(" ❌ This should not print: %s", missing_value)
    except ValueError:
        logger.info(" ✅ Correctly raised ValueError for invalid type")


def main() -> None:
    """Main function to demonstrate  metadata functionality."""
    try:
        # Cleanup an existing database
        db_manager.connect(cleanup_existing=True)

        # Load existing dataset
        dataset, samples = load_existing_dataset()

        # Add bulk metadata
        add_bulk_metadata(db_manager.persistent_session(), [s.sample_id for s in samples])

        # Add individual metadata
        add_individual_metadata(samples)

        # Demonstrate different types of filtering
        demonstrate_bulk_metadata_filters(dataset)
        demonstrate_individual_metadata_filters(dataset)
        demonstrate_combined_filters(dataset)
        demonstrate_dictionary_like_access(samples)

        ls.start_gui()

    except ValueError as e:
        logger.error("❌ Error: %s", e)
        logger.error("\n💡 Make sure to set the environment variables:")
        logger.error("   export EXAMPLES_DATASET_PATH=/path/to/your/dataset")
    except Exception as e:
        logger.exception("❌ Unexpected error: %s", e)


if __name__ == "__main__":
    main()
