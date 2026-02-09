import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

# Indexes the dataset, creates embeddings and stores everything in the database. Here we only load images.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Start the UI server on port 8001. Use env variables to change port and host:
# LIGHTLY_STUDIO_PORT=8002
# LIGHTLY_STUDIO_HOST=0.0.0.0
ls.start_gui()