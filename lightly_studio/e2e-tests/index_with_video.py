"""End-to-end demonstration of the lightly_studio indexing video."""

# We import the DatasetLoader class from the lightly_purple module
from pathlib import Path

import lightly_studio as ls

current_dir = Path(__file__).resolve().parent

# Clean up an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader instance
dataset = ls.Dataset.create(sample_type=ls.SampleType.VIDEO)
dataset.add_videos_from_path(path="dataset_examples/youtube_vis_50_videos")

ls.start_gui()
