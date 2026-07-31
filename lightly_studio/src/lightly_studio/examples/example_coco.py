"""Example of how to add samples in coco format to a dataset."""

from environs import Env, EnvError

import lightly_studio as ls
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
try:
    annotations_json = env.path("EXAMPLES_COCO_JSON_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_COCO_JSON_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_COCO_JSON_PATH (see CONTRIBUTING.md)."
    ) from e
try:
    images_path = env.path("EXAMPLES_COCO_IMAGES_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_COCO_IMAGES_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_COCO_IMAGES_PATH (see CONTRIBUTING.md)."
    ) from e

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco(
    annotations_json=annotations_json,
    images_path=images_path,
    annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
)

ls.start_gui()
