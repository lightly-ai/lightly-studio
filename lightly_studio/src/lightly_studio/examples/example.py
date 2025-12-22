"""Example of how to add samples in coco format to a dataset."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path("EXAMPLES_COCO_JSON_PATH", "/Users/leonardo/www/dataset_examples/coco_subset_128_images/instances_train2017.json")
images_path = env.path("EXAMPLES_COCO_IMAGES_PATH", "/Users/leonardo/www/dataset_examples/coco_subset_128_images/images")

# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_coco(
    annotations_json=annotations_json,
    images_path=images_path,
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

ls.start_gui()
