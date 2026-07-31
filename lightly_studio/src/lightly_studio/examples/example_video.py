"""Example of how to load videos from path with the dataset class."""

from environs import Env, EnvError

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
try:
    dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_VIDEO_DATASET_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_VIDEO_DATASET_PATH (see CONTRIBUTING.md)."
    ) from e

# Create a Dataset from a path
dataset = VideoDataset.create()
dataset.add_videos_from_path(path=dataset_path, target_fps=1)

ls.start_gui()
