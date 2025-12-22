"""End-to-end demonstration of the lightly_studio indexing video."""

import lightly_studio as ls
from lightly_studio.core.video_dataset import VideoDataset

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

dataset = VideoDataset.create()
dataset.add_videos_from_path(path="datasets/youtube_vis_50_videos")

ls.start_gui()
