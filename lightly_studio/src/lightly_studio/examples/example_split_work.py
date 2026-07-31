"""Example of how to add tags to samples to set up a split review workflow."""

import math

from environs import Env, EnvError

import lightly_studio as ls
from lightly_studio.database import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a Dataset instance
dataset = ls.ImageDataset.create()

# Define the path to the dataset (folder containing data.yaml)
try:
    dataset_path = env.path("EXAMPLES_YOLO_YAML_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_YOLO_YAML_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_YOLO_YAML_PATH (see CONTRIBUTING.md)."
    ) from e
input_split = env.str("EXAMPLES_YOLO_SPLIT", "test")

# Load YOLO dataset using data.yaml path
dataset.add_samples_from_yolo(
    data_yaml=dataset_path,
    input_split=input_split,
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
