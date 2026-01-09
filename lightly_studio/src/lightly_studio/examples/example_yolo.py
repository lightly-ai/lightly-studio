"""Example of how to add samples in yolo format to a dataset."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_YOLO_YAML_PATH", "/path/to/your/dataset/data.yaml")
input_split = env.str("EXAMPLES_YOLO_SPLIT", "train")

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_yolo(data_yaml=dataset_path, input_split=input_split)
ls.start_gui()
