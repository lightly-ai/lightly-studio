"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

# We import the DatasetLoader class from the lightly_studio module
import lightly_studio as ls

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader instance
dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json="datasets/coco_subset_128_images/captions_train2017.json",
    images_path="datasets/coco_subset_128_images/images",
)

ls.start_gui()
