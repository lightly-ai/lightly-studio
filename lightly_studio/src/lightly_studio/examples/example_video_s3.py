"""Example of how to load videos from path with the dataset class."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.video.video_dataset import VideoDataset

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = "s3://studio-test-datasets-eu/youtube_vis_50_videos/train/"

# Create a Dataset from a path
dataset = VideoDataset.create()
dataset.add_videos_from_path(path=dataset_path)

ls.start_gui()
