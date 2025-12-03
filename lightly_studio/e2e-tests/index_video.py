"""End-to-end demonstration of the lightly_studio indexing video."""

import lightly_studio as ls

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

dataset = ls.Dataset.create(sample_type=ls.SampleType.VIDEO)
dataset.add_videos_from_path(path="datasets/youtube_vis_50_videos")

ls.start_gui()
