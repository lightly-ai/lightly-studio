"""End-to-end demonstration of indexing video with annotations in YouTube-VIS format."""

from __future__ import annotations

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import AnnotationType

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a Dataset from a path
dataset = VideoDataset.create()
dataset.add_videos_from_youtube_vis(
    annotations_json="datasets/youtube_vis_50_videos/train/instances_50.json",
    videos_path="datasets/youtube_vis_50_videos/train/videos",
    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
    embed=False,
)

# Start the GUI
ls.start_gui()
