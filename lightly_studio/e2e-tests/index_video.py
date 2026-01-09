"""End-to-end demonstration of indexing video with annotations in YouTube-VIS format."""

from __future__ import annotations

from pathlib import Path

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.video_dataset import VideoDataset
from lightly_studio.utils.video_annotations_helpers import load_annotations

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a Dataset from a path
dataset = VideoDataset.create()
dataset.add_videos_from_path(path="datasets/youtube_vis_50_videos", embed=False)

# Load annotations
load_annotations(
    session=dataset.session,
    collection_id=dataset.dataset_id,
    annotations_path=Path("datasets/youtube_vis_50_videos/train/instances_50.json"),
)

# Start the GUI
ls.start_gui()
