"""This example of loading several datasets and launching the UI."""

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.image_dataset import ImageDataset
from lightly_studio.core.video_dataset import VideoDataset

# Connect to the database
db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

# Create dataset with images
dataset = ImageDataset.create(name="dataset_with_images")
dataset.add_images_from_path(path="dataset_examples/coco_subset_128_images/images", embed=False)

# Create second dataset with videos
video_dataset = VideoDataset.create(name="dataset_with_videos")
video_dataset.add_videos_from_path(path="dataset_examples/youtube_vis_50_videos", embed=False)

ls.start_gui()
