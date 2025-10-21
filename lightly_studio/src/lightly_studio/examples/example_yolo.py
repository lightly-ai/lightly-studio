"""Example of how to add samples in yolo format to a dataset."""

from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = Path(env.path("DATASET_PATH", "/path/to/your/dataset"))

# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_yolo(data_yaml=dataset_path, input_split="train")

ls.start_gui()
