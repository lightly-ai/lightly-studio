"""Example of how to run selection class."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

# Run selection via the dataset query
dataset.query().selection().diverse(
    n_samples_to_select=10,
    selection_result_tag_name="diverse_selection",
)

ls.start_gui()
