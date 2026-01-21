"""Example of how to load videos with annotations in YouTube-VIS format."""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.video_dataset import VideoDataset

if __name__ == "__main__":
    # Read environment variables
    env = Env()
    env.read_env()

    # Cleanup an existing database
    db_manager.connect(cleanup_existing=True)

    # Define the path to the dataset directory
    dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")
    annotations_path = env.path(
        "EXAMPLES_VIDEO_YVIS_JSON_PATH", "/path/to/your/dataset/instances.json"
    )

    # Create a Dataset from a path
    dataset = VideoDataset.create()
    dataset.add_samples_from_youtube_vis(
        annotations_json=annotations_path,
        path=dataset_path,
    )

    # Start the GUI
    ls.start_gui()
