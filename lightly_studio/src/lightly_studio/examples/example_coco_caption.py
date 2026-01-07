"""Example of how to add samples in coco caption format to a dataset."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path(
    "EXAMPLES_COCO_CAPTION_JSON_PATH", "/path/to/your/dataset/annotations.json"
)
images_path = env.path("EXAMPLES_COCO_CAPTION_IMAGES_PATH", "/path/to/your/dataset")


# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json=annotations_json,
    images_path=images_path,
)

ls.start_gui()
