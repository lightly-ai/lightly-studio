import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

ls.start_gui()