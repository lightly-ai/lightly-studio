"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

import lightly_studio as ls

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a Dataset instance
dataset = ls.ImageDataset.create()

# We point to the annotations json file and the input images folder.
# Defined dataset is processed here to be available for the UI application.
dataset.add_samples_from_coco(
    annotations_json="datasets/coco_subset_128_images/instances_train2017.json",
    images_path="datasets/coco_subset_128_images/images",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

# We start the UI application on port 8001
ls.start_gui()
