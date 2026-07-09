"""Example of adding custom, precomputed embeddings to a dataset.

Use `Sample.set_embedding` to plug in embeddings from your own model instead of
relying on the built-in embedding pipeline. This enables the embedding plot,
image-based similarity, and embedding-based sampling strategies. Load the dataset
with `embed=False` so the built-in model never runs.

Note: text-based search does not work with custom embeddings, since there is no
text encoder for a custom embedding space. The GUI hides the search bar
automatically.
"""

import numpy as np
from environs import Env
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path, skipping the built-in embedding pipeline.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path, embed=False)


def compute_custom_embedding(file_path: str) -> list[float]:
    """Stand-in for your own model: the mean RGB color of the image."""
    with Image.open(file_path) as image:
        pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
    return [float(value) for value in pixels.mean(axis=(0, 1))]


for sample in dataset:
    embedding = compute_custom_embedding(sample.file_path_abs)
    sample.set_embedding(embedding)

ls.start_gui()
