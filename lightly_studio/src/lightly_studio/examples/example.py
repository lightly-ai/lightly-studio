"""Example of how to load samples from path with the dataset class."""

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
    dataset_path = env.path("EXAMPLES_DATASET_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_DATASET_PATH is not set. Run `cp .env.example .env` in "
        "lightly_studio/ and set EXAMPLES_DATASET_PATH (see CONTRIBUTING.md)."
    ) from e

# Create a Dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

for sample in dataset:
    print(sample)

ls.start_gui()
