"""This example of loading several datasets and launching the UI."""

import lightly_studio as ls
from lightly_studio import db_manager

# Connect to the database
db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

# Create dataset with images
# dataset = ImageDataset.create(name="dataset_with_images")
# dataset.add_images_from_path(path="dataset_examples/coco_subset_128_images/images", embed=False)

# Create second dataset with videos
# video_dataset = VideoDataset.create(name="dataset_with_videos")
# video_dataset.add_videos_from_path(path="dataset_examples/youtube_vis_50_videos", embed=False)


# Create dataset and add images
dataset = ls.ImageDataset.create(name="evaluation_example_dataset")
dataset.add_images_from_path(path="dataset_examples/coco_subset_128_images/images")

# Add two different annotation collections from COCO
dataset.add_annotations_from_coco(
    annotations_json="dataset_examples/coco_subset_128_images/instances_train2017.json",
    images_root="dataset_examples/coco_subset_128_images/images",
    annotation_source="Ground truth",
)

dataset.add_annotations_from_coco(
    annotations_json="dataset_examples/coco_subset_128_images/predictions_train2017.json",
    images_root="dataset_examples/coco_subset_128_images/images",
    annotation_source="Predictions",
)


ls.start_gui()
