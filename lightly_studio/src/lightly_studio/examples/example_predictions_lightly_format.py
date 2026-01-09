"""Example of how to add samples with predictions in Lightly format to a dataset."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
input_folder = env.path("EXAMPLES_LIGHTLY_PREDICTIONS", "/path/to/your/dataset/annotations.json")

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_lightly(input_folder=input_folder)

ls.start_gui()
