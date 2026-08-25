"""End-to-end demonstration of indexing a remote GCS dataset."""

import lightly_studio as ls
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.database import db_manager

# Connect to the database
db_manager.connect(cleanup_existing=True)

# Create a dataset with images from GCS.
# By default, gcsfs discovers credentials from the ADC well-known file.
dataset = ImageDataset.create(name="gcs_dataset")
dataset.add_images_from_path(path="gs://kondrat-test-bucket/coco_subset_128_images/", embed=False)

ls.start_gui()
