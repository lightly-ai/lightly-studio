"""Example of how to load Pascal VOC segmentations."""

import json
from pathlib import Path

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
    images_path = env.path("EXAMPLES_PASCALVOC_IMAGES_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_PASCALVOC_IMAGES_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_PASCALVOC_IMAGES_PATH (see CONTRIBUTING.md)."
    ) from e
try:
    masks_path = env.path("EXAMPLES_PASCALVOC_MASKS_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_PASCALVOC_MASKS_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_PASCALVOC_MASKS_PATH (see CONTRIBUTING.md)."
    ) from e

# A mapping from class IDs to class names must be provided. We load it from a JSON file,
# the file is not part of the Pascal VOC format.
try:
    class_id_to_name_path = env.path("EXAMPLES_PASCALVOC_CATEGORIES_JSON_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_PASCALVOC_CATEGORIES_JSON_PATH is not set. In lightly_studio/, clone the "
        "example dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_PASCALVOC_CATEGORIES_JSON_PATH "
        "(see CONTRIBUTING.md)."
    ) from e
json_dict = json.loads(Path(class_id_to_name_path).read_text())
class_id_to_name = {int(k): v for k, v in json_dict.items()}

# Create a dataset and load Pascal VOC masks as segmentation mask annotations.
dataset = ls.ImageDataset.create()
dataset.add_samples_from_pascal_voc_segmentations(
    images_path=images_path,
    masks_path=masks_path,
    class_id_to_name=class_id_to_name,
)

ls.start_gui()
