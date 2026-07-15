"""Index a dataset with configurable content for the distribution panel.

One script for every distribution-panel scenario; env vars toggle what gets
seeded (all default to true):

- ``ADD_CLASSIFICATIONS``   one weighted classification label per image
- ``ADD_OBJECT_DETECTIONS`` a few weighted detection boxes per image
- ``ADD_SEGMENTATIONS``     one or two weighted segmentation masks per image
- ``ADD_METADATA``          numeric metadata fields with distinct distribution
  shapes (bell, flat, skewed, discrete, constant) plus a string field —
  rendered as histograms in the panel's "Metadata" distribution and above the
  range sliders in the metadata filter panel

Examples::

    make start-e2e-distribution                        # everything
    ADD_METADATA=false make start-e2e-distribution     # annotations only
    ADD_CLASSIFICATIONS=false ADD_OBJECT_DETECTIONS=false \
        ADD_SEGMENTATIONS=false make start-e2e-distribution  # metadata only

Each annotation type uses a distinct, weighted class pool so the bar chart has
a clear shape per selection. Everything is synthetic, so the sole input
required is an images folder. Point it at any images you already have via
``EXAMPLES_IMAGES_PATH`` (defaults to the COCO subset used by
``index_general.py``).

Re-running recreates the dataset: it resets the local database on every run,
since DuckDB has no single-dataset delete.
"""

import random
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import numpy as np
from environs import Env
from numpy.typing import NDArray

import lightly_studio as ls
from lightly_studio.core.annotation.annotation_create import (
    CreateAnnotation,
    CreateClassification,
    CreateObjectDetection,
    CreateSegmentationMask,
)
from lightly_studio.database import db_manager
from lightly_studio.resolvers import metadata_resolver

env = Env()
env.read_env()

IMAGES_PATH = env.path("EXAMPLES_IMAGES_PATH", "datasets/coco_subset_128_images/images")

ADD_CLASSIFICATIONS = env.bool("ADD_CLASSIFICATIONS", True)
ADD_OBJECT_DETECTIONS = env.bool("ADD_OBJECT_DETECTIONS", True)
ADD_SEGMENTATIONS = env.bool("ADD_SEGMENTATIONS", True)
ADD_METADATA = env.bool("ADD_METADATA", True)

DATASET_NAME = "distribution_example_dataset"
RANDOM_SEED = 42

# Distinct, weighted class pools per type so each distribution has a clear shape.
CLASSIFICATION_CLASSES = ["daytime", "night", "dawn", "dusk", "indoor"]
CLASSIFICATION_WEIGHTS = [0.45, 0.25, 0.15, 0.1, 0.05]

DETECTION_CLASSES = ["car", "person", "bicycle", "traffic_light", "bus", "truck"]
DETECTION_WEIGHTS = [0.35, 0.3, 0.12, 0.1, 0.08, 0.05]

SEGMENTATION_CLASSES = ["road", "sky", "building", "vegetation", "sidewalk"]
SEGMENTATION_WEIGHTS = [0.3, 0.25, 0.2, 0.15, 0.1]

LOCATIONS = ["city", "rural", "mountain", "coastal", "desert"]


def _box(
    width: int, height: int, left_fraction: float, top_fraction: float
) -> tuple[int, int, int, int]:
    """Return an (x, y, w, h) box covering roughly a third of the image."""
    x = int(width * left_fraction)
    y = int(height * top_fraction)
    return x, y, min(max(1, width // 3), width - x), min(max(1, height // 3), height - y)


def _rectangle_mask(
    width: int, height: int, left_fraction: float, top_fraction: float
) -> NDArray[np.int_]:
    """Return a binary mask (height x width) with a filled rectangle."""
    x, y, w, h = _box(width, height, left_fraction, top_fraction)
    mask = np.zeros((height, width), dtype=np.int_)
    mask[y : y + h, x : x + w] = 1
    return mask


def _sample_metadata(rng: random.Random) -> Mapping[str, Any]:
    """Return one sample's metadata, each key with a distinct distribution."""
    return {
        "confidence": min(1.0, max(0.0, rng.gauss(0.75, 0.12))),
        "brightness": rng.uniform(0.0, 255.0),
        "object_size": rng.lognormvariate(3.0, 0.8),
        "temperature": rng.randint(10, 40),
        "num_defects": rng.choices([0, 1, 2, 3, 5, 8], [50, 25, 12, 7, 4, 2])[0],
        "sensor_gain": 1.0,
        "location": rng.choice(LOCATIONS),
    }


def main() -> None:
    """Create the dataset, seed the configured content, and launch the UI."""
    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    samples = list(dataset)
    rng = random.Random(RANDOM_SEED)

    for sample in samples:
        annotations: list[CreateAnnotation] = []

        if ADD_CLASSIFICATIONS:
            annotations.append(
                CreateClassification(
                    class_name=rng.choices(CLASSIFICATION_CLASSES, CLASSIFICATION_WEIGHTS)[0],
                    confidence=rng.uniform(0.6, 1.0),
                )
            )

        if ADD_OBJECT_DETECTIONS:
            for _ in range(rng.randint(1, 4)):
                x, y, w, h = _box(
                    sample.width, sample.height, rng.uniform(0.05, 0.6), rng.uniform(0.05, 0.6)
                )
                annotations.append(
                    CreateObjectDetection(
                        class_name=rng.choices(DETECTION_CLASSES, DETECTION_WEIGHTS)[0],
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=rng.uniform(0.5, 1.0),
                    )
                )

        if ADD_SEGMENTATIONS:
            for _ in range(rng.randint(1, 2)):
                annotations.append(
                    CreateSegmentationMask.from_binary_mask(
                        class_name=rng.choices(SEGMENTATION_CLASSES, SEGMENTATION_WEIGHTS)[0],
                        binary_mask=_rectangle_mask(
                            sample.width,
                            sample.height,
                            rng.uniform(0.05, 0.5),
                            rng.uniform(0.05, 0.5),
                        ),
                        confidence=rng.uniform(0.5, 1.0),
                    )
                )

        if annotations:
            sample.add_annotations(annotations=annotations)

    if ADD_METADATA:
        sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = [
            (sample.sample_id, _sample_metadata(rng)) for sample in samples
        ]
        metadata_resolver.bulk_update_metadata(db_manager.persistent_session(), sample_metadata)

    seeded = [
        name
        for name, enabled in [
            ("classifications", ADD_CLASSIFICATIONS),
            ("object detections", ADD_OBJECT_DETECTIONS),
            ("segmentation masks", ADD_SEGMENTATIONS),
            ("numeric metadata", ADD_METADATA),
        ]
        if enabled
    ]
    print(
        f"Created dataset '{DATASET_NAME}' with {len(samples)} images and "
        f"{', '.join(seeded) if seeded else 'no extra content'}."
    )
    ls.start_gui()


if __name__ == "__main__":
    main()
