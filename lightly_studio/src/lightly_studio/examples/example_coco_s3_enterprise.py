"""Example of how to add samples in coco format to a dataset."""

import lightly_studio as ls

ls.connect()

# Define data paths
annotations_json = "s3://studio-test-datasets-eu/coco_subset_128_images/instances_train2017.json"
images_path = "s3://studio-test-datasets-eu/coco_subset_128_images/images"

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create(name="s3")
dataset.add_samples_from_coco(
    annotations_json=annotations_json,
    images_path=images_path,
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)
