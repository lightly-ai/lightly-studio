"""Example of how to create a dataset with semantic segmentation annotations."""

import json
from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
images_path = env.path("EXAMPLES_PASCALVOC_IMAGES_PATH", "/path/to/your/dataset/images")
masks_path = env.path("EXAMPLES_PASCALVOC_MASKS_PATH", "/path/to/your/dataset/masks")

# A mapping from class IDs to class names must be provided. We load it from a JSON file,
# the file is not part of the Pascal VOC format.
class_id_to_name_path = env.path(
    "EXAMPLES_PASCALVOC_CATEGORIES_JSON_PATH",
    "/path/to/your/dataset/class_id_to_name.json",
)
class_id_to_name = {
    int(k): v for k, v in json.loads(Path(class_id_to_name_path).read_text()).items()
}

# Create a Dataset and add load samples with semantic segmentation annotations
dataset = ls.ImageDataset.create()
dataset.add_samples_from_pascal_voc_segmentations(
    images_path=images_path,
    masks_path=masks_path,
    class_id_to_name=class_id_to_name,
)

# TODO(Michal, 01/2026): Add frontend support for displaying semantic segmentations.
# ls.start_gui()
