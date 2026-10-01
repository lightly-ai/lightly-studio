"""Example of importing ActivityNet-style temporal annotations."""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

videos_path = env.path(
    "EXAMPLES_ACTIVITYNET_VIDEOS_PATH",
    "dataset_examples/activitynet_10_videos/videos",
)
annotations_path = env.path(
    "EXAMPLES_ACTIVITYNET_JSON_PATH",
    "dataset_examples/activitynet_10_videos/activity_net.v1-3.min.json",
)

dataset = VideoDataset.create()
dataset.add_videos_from_path(path=videos_path, embed=False, embed_frames=False, target_fps=1)
dataset.add_annotations_from_activitynet(
    annotations_json=annotations_path,
    annotation_source="activitynet",
)

# Print the loaded annotations per video.
for video in dataset:
    print(f"{video.file_name}: {len(video.annotations)} annotation(s)")
    for annotation in video.annotations:
        span = annotation.annotation_base.temporal_span_details
        time_range = f"{span.start_time_s:.2f}s - {span.end_time_s:.2f}s" if span else "no span"
        print(f"  - {annotation.class_name} [{time_range}] (confidence: {annotation.confidence})")

ls.start_gui()
