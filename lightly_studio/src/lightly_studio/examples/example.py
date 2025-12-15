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
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path
dataset = ls.Dataset.create()
dataset.add_images_from_path(path=dataset_path)

for sample in dataset:
    print(sample)

# Second dataset

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_YOLO_YAML_PATH", "/path/to/your/dataset/data.yaml")
input_split = env.str("EXAMPLES_YOLO_SPLIT", "train")

# Create a DatasetLoader from a path
dataset2 = ls.Dataset.create(name="YOLO Dataset")
dataset2.add_samples_from_yolo(data_yaml=dataset_path, input_split=input_split)


ls.start_gui()
