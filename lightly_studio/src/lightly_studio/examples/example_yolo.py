"""Example of how to add samples in yolo format to a dataset."""

from environs import Env, EnvError

import lightly_studio as ls
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
try:
    dataset_path = env.path("EXAMPLES_YOLO_YAML_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_YOLO_YAML_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_YOLO_YAML_PATH (see CONTRIBUTING.md)."
    ) from e
input_split = env.str("EXAMPLES_YOLO_SPLIT", "train")

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_yolo(data_yaml=dataset_path, input_split=input_split)
ls.start_gui()
