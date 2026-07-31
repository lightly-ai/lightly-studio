"""Example of how to add samples with predictions in Lightly format to a dataset."""

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
    input_folder = env.path("EXAMPLES_LIGHTLY_PREDICTIONS")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_LIGHTLY_PREDICTIONS is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_LIGHTLY_PREDICTIONS (see CONTRIBUTING.md)."
    ) from e

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_lightly(input_folder=input_folder)

ls.start_gui()
