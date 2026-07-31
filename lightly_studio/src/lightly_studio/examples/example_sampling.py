"""Example of how to run sampling class."""

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
        "EXAMPLES_DATASET_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_DATASET_PATH (see CONTRIBUTING.md)."
    ) from e

# Create a Dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

# Run sampling via the dataset query
dataset.query().sampling().diverse(
    n_samples_to_select=10,
    sampling_result_tag_name="diverse_sampling",
)

ls.start_gui()
