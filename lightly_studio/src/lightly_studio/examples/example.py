"""Example of how to load samples from path with the dataset class."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")
annotations_path = env.path("EXAMPLES_VIDEO_YVIS_JSON_PATH", "/path/to/your/dataset/instances.json")

# Create a Dataset from a path
dataset = ls.VideoDataset.create()
dataset.add_videos_from_youtube_vis(
    annotations_json=annotations_path,
    videos_path=dataset_path,
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

ls.start_gui()
