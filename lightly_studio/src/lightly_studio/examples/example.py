"""Example of how to load samples from path with the dataset class."""

from io import BytesIO

import av
import fsspec

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    video_frame_resolver,
    video_resolver,
)

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory

# Create a Dataset from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_path(path=dataset_path)

for sample in dataset:
    print(sample)

ls.start_gui()
