"""Example script demonstrating metadata capabilities.

This script shows how to:
1. Load an existing dataset using DatasetLoader
2. Add metadata to all samples using bulk operations
3. Add metadata to individual samples
4. Filter samples using various metadata types
"""

from __future__ import annotations

import random
import time
from uuid import UUID

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import Metadata
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

# Environment variables
env = Env()
env.read_env()
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")


def load_existing_dataset() -> tuple[ls.ImageDataset, list[ImageSample]]:
    """Load an existing dataset using DatasetLoader.

    Returns:
        Tuple of (dataset, samples).
    """
    print(" Loading existing dataset...")

    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=dataset_path)

    # Get all samples from the dataset
    samples = dataset.query().to_list()

    print(f"✅ Loaded dataset with {len(samples)} samples")
    return dataset, samples


def add_bulk_metadata(session: Session, sample_ids: list[UUID]) -> None:
    """Add metadata to all samples using bulk operations."""
    print("\n Adding bulk metadata to all samples...")

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

    print(f"✅ Added metadata to {len(sample_ids)} samples in {elapsed_time:.2f}s")


def add_individual_metadata(samples: list[ImageSample]) -> None:
    """Add metadata to individual samples."""
    print("\n Adding individual metadata to specific samples...")

    # Add metadata to first 5 samples individually
    for i, sample in enumerate(samples[:5]):
        print(f" Adding metadata to sample {sample.file_name} {sample.sample_id}...")
        # Add some specific metadata
        sample.metadata["special_metadata"] = f"sample_{i + 1}_special"
        sample.metadata["priority"] = random.randint(1, 10)
        sample.metadata["list"] = [1, 2, 3]
        sample.metadata["custom_gps"] = GPSCoordinate(
            lat=40.7128 + i * 0.1,  # Slightly different coordinates
            lon=-74.0060 + i * 0.1,
        )

    print(f"✅ Added individual metadata to {min(5, len(samples))} samples")


def demonstrate_bulk_metadata_filters(dataset: ls.ImageDataset) -> None:
    """Demonstrate filtering with bulk-added metadata."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    print("\n Bulk Metadata Filters:")
    print("=" * 50)

    # Filter by temperature
    print("\n1. Filter by temperature > 25:")
    filter_temp = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("temperature") > 25])  # noqa PLR2004
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_temp,
    ).samples
    print(f"   Found {len(images)} samples with temperature > 25")
    for image in images[:3]:  # Show first 3
        print(f" {image.file_name}: {image.sample['temperature']}")

    # Filter by location
    print("\n2. Filter by location == 'city':")
    filter_location = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("location") == "city"])
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_location,
    ).samples
    print(f"   Found {len(images)} samples from cities")
    for image in images[:3]:  # Show first 3
        print(f" {image.file_name}: {image.sample['location']}")

    # Filter by GPS coordinates
    print("\n3. Filter by latitude > 0° (Northern hemisphere):")
    filter_lat = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("gps_coordinates.lat") > 0])
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_lat,
    ).samples
    print(f"   Found {len(images)} samples in Northern hemisphere")
    for image in images[:3]:  # Show first 3
        gps = image.sample["gps_coordinates"]
        print(f" {image.file_name}: lat={gps.lat:.4f}, lon={gps.lon:.4f}")

    # Filter by confidence
    print("\n4. Filter by high confidence (> 0.9):")
    filter_confidence = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("confidence") > 0.9]  # noqa PLR2004
        )
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_confidence,
    ).samples
    print(f"   Found {len(images)} samples with confidence > 0.9")
    for image in images[:3]:  # Show first 3
        print(f"   📸 {image.file_name}: confidence={image.sample['confidence']:.3f}")


def demonstrate_individual_metadata_filters(dataset: ls.ImageDataset) -> None:
    """Demonstrate filtering with individually-added metadata."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    print("\n Individual Metadata Filters:")
    print("=" * 50)

    # Filter by special metadata
    print("\n1. Filter by special metadata (individually added):")
    filter_special = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("special_metadata") == "sample_1_special"]
        )
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_special,
    ).samples
    print(f"   Found {len(images)} samples with special metadata")
    for image in images:
        print(f" {image.file_name}: {image.sample['special_metadata']}")

    # Filter by priority
    print("\n2. Filter by high priority (> 7):")
    filter_priority = ImageFilter(
        sample_filter=SampleFilter(metadata_filters=[Metadata("priority") > 7])  # noqa PLR2004
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_priority,
    ).samples
    print(f"   Found {len(images)} samples with priority > 7")
    for image in images:
        print(f" {image.file_name}: priority={image.sample['priority']}")

    # Filter by custom GPS
    print("\n3. Filter by custom GPS coordinates:")
    filter_custom_gps = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[Metadata("custom_gps.lat") > 40.8]  # noqa PLR2004
        )
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_custom_gps,
    ).samples
    print(f"   Found {len(images)} samples with custom GPS lat > 40.8")
    for image in images:
        gps = image.sample["custom_gps"]
        print(f" {image.file_name}: lat={gps.lat:.4f}, lon={gps.lon:.4f}")


def demonstrate_combined_filters(dataset: ls.ImageDataset) -> None:
    """Demonstrate combining multiple filters."""
    # TODO(Michal, 09/2025): Update with native metadata filtering instead of accessing
    print("\n Combined Filters:")
    print("=" * 50)

    # Multiple conditions
    print("\n1. Find high-confidence, processed, warm images:")
    filter_combined = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                Metadata("confidence") > 0.8,  # noqa PLR2004
                Metadata("is_processed") == True,  # noqa E712
                Metadata("temperature") > 25,  # noqa PLR2004
            ]
        )
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_combined,
    ).samples
    print(f"   Found {len(images)} samples matching all criteria")
    for image in images[:3]:
        print(
            f" {image.file_name}: conf={image.sample['confidence']:.2f}, "
            f"temp={image.sample['temperature']}, processed={image.sample['is_processed']}"
        )

    # Complex GPS + other filters
    print("\n2. Find northern hemisphere, high-confidence images:")
    filter_gps_combined = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                Metadata("gps_coordinates.lat") > 0,  # Northern hemisphere
                Metadata("confidence") > 0.85,  # noqa PLR2004
                Metadata("location") == "city",
            ]
        )
    )
    images = image_resolver.get_all_by_collection_id(
        session=dataset.session,
        collection_id=dataset.dataset_id,
        filters=filter_gps_combined,
    ).samples
    print(f"   Found {len(images)} samples in northern hemisphere cities with high confidence")
    for image in images[:3]:
        gps = image.sample["gps_coordinates"]
        print(f" {image.file_name}: lat={gps.lat:.4f}, conf={image.sample['confidence']:.2f}")


def demonstrate_dictionary_like_access(samples: list[ImageSample]) -> None:
    """Demonstrate adding metadata using dictionary-like access."""
    print("\n Dictionary-like Metadata Access:")
    print("=" * 50)

    # Get the first few samples to demonstrate
    samples = samples[:2]

    print("\n1. Adding metadata using sample.metadata['key'] = value syntax:")

    # Add different types of metadata to different samples
    samples[0].metadata["temperature"] = 25
    samples[0].metadata["location"] = "city"
    samples[0].metadata["is_processed"] = True
    samples[0].metadata["confidence"] = 0.95
    print(
        f" {samples[0].file_name}: "
        f"temp={samples[0].metadata['temperature']}°C, "
        f"location={samples[0].metadata['location']}, "
        f"processed={samples[0].metadata['is_processed']}"
    )

    samples[1].metadata["temperature"] = 15
    samples[1].metadata["location"] = "mountain"
    samples[1].metadata["gps_coordinates"] = GPSCoordinate(lat=40.7128, lon=-74.0060)
    samples[1].metadata["tags"] = ["outdoor", "nature", "landscape"]
    print(
        f" {samples[1].file_name}: temp={samples[1].metadata['temperature']}°C, "
        f"location={samples[1].metadata['location']}, tags={samples[1].metadata['tags']}"
    )

    # Demonstrate reading metadata
    print("\n2. Reading metadata using sample.metadata['key'] syntax:")
    for sample in samples:
        print(f" {sample.file_name}:")
        print(f"      Temperature: {sample.metadata['temperature']}°C")
        print(f"      Location: {sample.metadata['location']}")
        gps = sample.metadata["gps_coordinates"]
        print(f"      GPS: lat={gps.lat:.4f}, lon={gps.lon:.4f}")
        print(f"      Tags: {sample.metadata['tags']}")

    # Demonstrate None return for missing keys
    print("  Note: sample.metadata['key'] returns None for missing keys")
    missing_value = samples[0].metadata["nonexistent_key"]
    if missing_value is None:
        print(f" sample.metadata['nonexistent_key']: {missing_value}")

    print(f"✅ Added metadata to {len(samples)} samples using dictionary-like access")

    # Demonstrate schema presentation
    try:
        samples[0].metadata["temperature"] = "string_value"  # Invalid type for demonstration
        print(f" ❌ This should not print: {missing_value}")
    except ValueError:
        print(" ✅ Correctly raised ValueError for invalid type")


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
        print(f"❌ Error: {e}")
        print("\n💡 Make sure to set the environment variables:")
        print("   export EXAMPLES_DATASET_PATH=/path/to/your/dataset")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
