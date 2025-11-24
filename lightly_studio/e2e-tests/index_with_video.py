"""End-to-end demonstration of the lightly_studio indexing video."""

# We import the DatasetLoader class from the lightly_purple module
from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Create a DatasetLoader instance
db_manager.connect(cleanup_existing=True)

current_dir = Path(__file__).resolve().parent


# Create a Dataset from a path
dataset = ls.Dataset.create(sample_type=ls.SampleType.VIDEO)
dataset.add_videos_from_path(path="datasets/small_videos")

ls.start_gui()
