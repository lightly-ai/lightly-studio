"""Example of how to load videos from path with the dataset class."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path
dataset = ls.Dataset.create(sample_type=ls.SampleType.VIDEO)
dataset.add_videos_from_path(path="C:\\Users\\horatiu\\Videos\\edge_demo.mp4")

ls.start_gui()
