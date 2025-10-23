"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

from lightly_studio import AnnotationType, Dataset, db_manager, start_gui

# Clean up an existing database
db_manager.connect(cleanup_existing=True)

# Create a Dataset instance
dataset = Dataset.create()

# We point to the annotations json file and the input images folder.
# Defined dataset is processed here to be available for the UI application.
dataset.add_samples_from_coco(
    annotations_json="datasets/coco-128/instances_train2017.json",
    images_path="datasets/coco-128/images",
    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
)

# We start the UI application on port 8001
start_gui()
