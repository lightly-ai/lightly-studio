"""Example of how to load samples from path with the dataset class."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("DATASET_PATH", "../../../../yolo-data-example/dataset.yaml")

# Create a Dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_yolo(
    str(dataset_path),
    input_split=env.str("PURPLE_DATASET_SPLIT", "test"),
)
for sample in dataset:
    print(sample)

ls.start_gui()
