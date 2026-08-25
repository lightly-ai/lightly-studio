"""End-to-end demonstration of indexing a remote S3 dataset."""

import lightly_studio as ls
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.database import db_manager

db_manager.connect(cleanup_existing=True)

# Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or ~/.aws/credentials.
dataset = ImageDataset.create(name="s3_dataset")
dataset.add_images_from_path(path="s3://<your-bucket>/coco_subset_128_images/", embed=False)

ls.start_gui()
