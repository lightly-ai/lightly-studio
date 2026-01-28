"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""
import random

import lightly_studio as ls
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import metadata_resolver

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a Dataset instance
dataset = ls.ImageDataset.load_or_create(name="default_dataset")

# We point to the annotations json file and the input images folder.
# Defined dataset is processed here to be available for the UI application.
dataset.add_samples_from_coco(
    annotations_json="datasets/coco_subset_128_images/instances_train2017.json",
    images_path="datasets/coco_subset_128_images/images",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

sample_metadata = []
for sample in dataset:
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
            sample.sample_id,
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
metadata_resolver.bulk_update_metadata(dataset.session, sample_metadata)

# We start the UI application on port 8001
ls.start_gui()
