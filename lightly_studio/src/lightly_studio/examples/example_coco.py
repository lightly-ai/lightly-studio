"""Example of how to add samples in coco format to a dataset."""

import lightly_studio as ls
from lightly_studio import db_manager

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_coco(
    annotations_json="/path/to/your/dataset",
    images_path="/path/to/your/dataset",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

ls.start_gui()
