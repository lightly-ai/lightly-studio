"""Index a dataset with a mix of annotation types for the distribution panel.

Creates classification, object-detection, and segmentation-mask annotations on a
single image dataset so the Dataset Distribution panel's annotation-type selector
("All types" / Classification / Object detection / Segmentation) has data to show
for every option. Each type uses a distinct, weighted class pool so the bar chart
has a clear shape per selection.

Annotations are synthetic, so the only input required is an images folder. Point
it at any images you already have via ``EXAMPLES_IMAGES_PATH`` (defaults to the
COCO subset used by ``index_general.py``).

Re-running recreates the dataset: it resets the local database on every run, since
DuckDB has no single-dataset delete.
"""

import random

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

env = Env()
env.read_env()

IMAGES_PATH = env.path("EXAMPLES_IMAGES_PATH", "datasets/coco_subset_128_images/images")

DATASET_NAME = "distribution_example_dataset"
RANDOM_SEED = 42

# Distinct, weighted class pools per type so each distribution has a clear shape.
CLASSIFICATION_CLASSES = ["daytime", "night", "dawn", "dusk", "indoor"]
CLASSIFICATION_WEIGHTS = [0.45, 0.25, 0.15, 0.1, 0.05]

DETECTION_CLASSES = ["car", "person", "bicycle", "traffic_light", "bus", "truck"]
DETECTION_WEIGHTS = [0.35, 0.3, 0.12, 0.1, 0.08, 0.05]

SEGMENTATION_CLASSES = ["road", "sky", "building", "vegetation", "sidewalk"]
SEGMENTATION_WEIGHTS = [0.3, 0.25, 0.2, 0.15, 0.1]


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


def main() -> None:
    """Create the dataset, synthesize mixed annotations, and launch the UI."""
    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    samples = list(dataset)
    rng = random.Random(RANDOM_SEED)

    for sample in samples:
        annotations: list[CreateAnnotation] = []

        # One classification label per image.
        annotations.append(
            CreateClassification(
                class_name=rng.choices(CLASSIFICATION_CLASSES, CLASSIFICATION_WEIGHTS)[0],
                confidence=rng.uniform(0.6, 1.0),
            )
        )

        # A few object-detection boxes per image.
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

        # One or two segmentation masks per image.
        for _ in range(rng.randint(1, 2)):
            annotations.append(
                CreateSegmentationMask.from_binary_mask(
                    class_name=rng.choices(SEGMENTATION_CLASSES, SEGMENTATION_WEIGHTS)[0],
                    binary_mask=_rectangle_mask(
                        sample.width, sample.height, rng.uniform(0.05, 0.5), rng.uniform(0.05, 0.5)
                    ),
                    confidence=rng.uniform(0.5, 1.0),
                )
            )

        sample.add_annotations(annotations=annotations)

    print(
        f"Created dataset '{DATASET_NAME}' with {len(samples)} images and classification, "
        "object-detection, and segmentation-mask annotations."
    )
    ls.start_gui()


if __name__ == "__main__":
    main()
