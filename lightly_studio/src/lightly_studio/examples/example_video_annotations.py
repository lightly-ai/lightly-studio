"""Example of how to load videos with annotations in YouTube-VIS format."""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import AnnotationType

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")
annotations_path = env.path("EXAMPLES_VIDEO_YVIS_JSON_PATH", "/path/to/your/dataset/instances.json")

# Create a Dataset from a path
dataset = VideoDataset.create()
dataset.add_videos_from_youtube_vis(
    annotations_json=annotations_path,
    videos_path=dataset_path,
    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
)

# Start the GUI
ls.start_gui()
