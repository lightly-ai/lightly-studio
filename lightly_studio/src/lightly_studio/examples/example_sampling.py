"""Example of how to run sampling class.

Also seeds custom metadata and a few sample tags so every metadata-distribution
plot feature can be tried in the GUI (open the "Distribution" side panel and pick
the "Metadata" source):

- Categorical keys (``weather``, ``scene``, ``is_daytime``) render as bar charts.
  ``weather`` is intentionally missing on ~15% of samples so the plot shows an
  explicit ``(none)`` bar.
- Numerical keys (``object_count``, ``brightness``) render as histograms.
- The "Compare tags" chips overlay one series per tag — this script creates
  ``batch_A/B/C`` and ``bright`` tags, and the sampling run adds
  ``diverse_sampling`` — so you can compare 2-4 tags at once (normalized by
  default, toggle to counts).
- ``gps_coordinates`` additionally lets you try the GPS map.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import metadata_resolver

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

# Deterministic values so the plots look the same on every run.
random.seed(42)

WEATHER = ["sunny", "rainy", "cloudy", "foggy"]
SCENES = ["city", "highway", "rural"]

# Assign metadata (and a couple of comparison tags) to every sample.
samples = dataset.query().to_list()
sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = []
for index, sample in enumerate(samples):
    values: dict[str, Any] = {
        # Categorical -> grouped bar chart.
        "scene": random.choice(SCENES),
        "is_daytime": random.choice([True, False]),
        # Numerical -> histogram.
        "object_count": random.randint(0, 40),
        "brightness": random.uniform(0.0, 1.0),
        # GPS -> map (roughly around Zurich).
        "gps_coordinates": GPSCoordinate(
            lat=random.uniform(47.0, 47.6),
            lon=random.uniform(8.0, 8.8),
        ),
    }
    # Leave ~15% of samples without a `weather` value so the plot shows a
    # "(none)" bucket.
    if random.random() > 0.15:  # noqa: PLR2004
        values["weather"] = random.choice(WEATHER)
    sample_metadata.append((sample.sample_id, values))

    # A few sample tags to overlay in the distribution plot's "Compare tags".
    sample.add_tag(f"batch_{'ABC'[index % 3]}")
    if values["brightness"] > 0.7:  # noqa: PLR2004
        sample.add_tag("bright")

metadata_resolver.bulk_update_metadata(db_manager.persistent_session(), sample_metadata)

# Run sampling via the dataset query (also produces a "diverse_sampling" tag).
dataset.query().sampling().diverse(
    n_samples_to_select=10,
    sampling_result_tag_name="diverse_sampling",
)

ls.start_gui()
