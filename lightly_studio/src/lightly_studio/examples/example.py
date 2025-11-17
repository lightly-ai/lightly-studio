"""Example of how to load samples from path with the dataset class."""

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
dataset_path = dataset_path.parent if dataset_path.is_file() else dataset_path

# Create a Dataset from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_path(path=dataset_path)

for sample in dataset:
    print(sample)

ls.start_gui()