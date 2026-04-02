"""Example of how to load Pascal VOC segmentations.
"""

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
json_dict = json.loads(Path(class_id_to_name_path).read_text())
class_id_to_name = {int(k): v for k, v in json_dict.items()}

# Create a dataset and load Pascal VOC masks as instance segmentation annotations.
dataset = ls.ImageDataset.create()
dataset.add_samples_from_pascal_voc_segmentations(
    images_path=images_path,
    masks_path=masks_path,
    class_id_to_name=class_id_to_name,
)
