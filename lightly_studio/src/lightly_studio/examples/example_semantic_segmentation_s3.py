"""Example of how to create a dataset with semantic segmentation annotations."""

import json

import fsspec
from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths.
dataset_uri = env.str("DATASET_URI", "s3://studio-test-datasets-eu/voc2012_10_images").rstrip("/")
images_path = f"{dataset_uri}/JPEGImages"
masks_path = f"{dataset_uri}/SegmentationClass"
class_id_to_name_path = f"{dataset_uri}/class_id_to_name.json"

# A mapping from class IDs to class names must be provided. We load it from a JSON file,
# the file is not part of the Pascal VOC format.
with fsspec.open(class_id_to_name_path, "r") as file:
    json_dict = json.load(file)
class_id_to_name = {int(k): v for k, v in json_dict.items()}

# Create a Dataset and add load samples with semantic segmentation annotations
dataset = ls.ImageDataset.create()
dataset.add_samples_from_pascal_voc_segmentations(
    images_path=images_path,
    masks_path=masks_path,
    class_id_to_name=class_id_to_name,
)

ls.start_gui()
