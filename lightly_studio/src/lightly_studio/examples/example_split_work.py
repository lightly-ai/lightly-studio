"""Example of how to add tags to samples to set up a split review workflow."""

import math

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a Dataset instance
dataset = ls.Dataset.create()

# Define the path to the dataset (folder containing data.yaml)
dataset_path = env.path("DATASET_PATH", "/path/to/your/yolo/dataset/data.yaml")

# Load YOLO dataset using data.yaml path
dataset.add_samples_from_yolo(
    data_yaml=str(dataset_path),
    input_split=env.str("LIGHTLY_STUDIO_DATASET_SPLIT", "test"),
)

# Define the reviewers
# This should be a comma-separated list of reviewers
# we will then create a tag for each reviewer and assign them samples
# to work on.
reviewers = env.str("DATASET_REVIEWERS", "Alice, Bob, Charlie, David")

# Create a tag for each reviewer to work on
tags = [reviewer.strip() for reviewer in reviewers.split(",")]

# Get all samples from the db
samples = dataset.query().to_list()

# Chunk the samples into portions equally divided among the reviewers.
chunk_size = math.ceil(len(samples) / len(tags))
for i, sample in enumerate(samples):
    sample.add_tag(tags[i // chunk_size])

# Launch the server to load data
ls.start_gui()
