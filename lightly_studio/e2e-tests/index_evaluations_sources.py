"""Index a dataset with synthetic sources for every supported evaluation task.

Use this to exercise the GUI evaluation trigger for all task types: it creates
``gt``/``pred`` annotation sources for object detection, classification, and
semantic segmentation on a single dataset, then launches the UI so you can open
the Evaluation panel and start runs.

Annotations are synthetic, so the only input required is an images folder
(bounding boxes and segmentation masks are generated to match each image's
dimensions). Point it at any images you already have via ``EXAMPLES_IMAGES_PATH``
(defaults to the COCO subset used by ``index_evaluations.py``).

Re-running recreates the dataset: it resets the local database on every run,
since DuckDB has no single-dataset delete.
"""

import random

import numpy as np
from environs import Env
from numpy.typing import NDArray

import lightly_studio as ls
from lightly_studio.core.annotation.annotation_create import (
    CreateClassification,
    CreateObjectDetection,
    CreateSegmentationMask,
)
from lightly_studio.database import db_manager
from lightly_studio.resolvers import annotation_resolver

env = Env()
env.read_env()

IMAGES_PATH = env.path("EXAMPLES_IMAGES_PATH", "datasets/coco_subset_128_images/images")

DATASET_NAME = "evaluation_all_sources_dataset"
CLASS_NAMES = ["cat", "dog", "bird"]
RANDOM_SEED = 42

OBJECT_DETECTION_GT_SOURCE = "object_detection_gt"
OBJECT_DETECTION_PRED_SOURCE = "object_detection_pred"
CLASSIFICATION_GT_SOURCE = "classification_gt"
CLASSIFICATION_PRED_SOURCE = "classification_pred"
SEGMENTATION_GT_SOURCE = "segmentation_gt"
SEGMENTATION_PRED_SOURCE = "segmentation_pred"


def _box(
    width: int, height: int, left_fraction: float, top_fraction: float
) -> tuple[int, int, int, int]:
    """Return an (x, y, w, h) box covering roughly half the image."""
    x = int(width * left_fraction)
    y = int(height * top_fraction)
    return x, y, min(max(1, width // 2), width - x), min(max(1, height // 2), height - y)


def _rectangle_mask(
    width: int,
    height: int,
    left_fraction: float,
    top_fraction: float,
) -> NDArray[np.int_]:
    """Return a binary mask (height x width) with a filled rectangle."""
    x, y, w, h = _box(width, height, left_fraction, top_fraction)
    mask = np.zeros((height, width), dtype=np.int_)
    mask[y : y + h, x : x + w] = 1
    return mask


def main() -> None:
    """Create the dataset, synthesize sources, and launch the UI."""
    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    samples = list(dataset)
    rng = random.Random(RANDOM_SEED)

    # --- Object-detection sources: a box per image; the prediction box is
    #     shifted so GT and prediction partially overlap. ---
    object_detection_gt = []
    object_detection_pred = []
    for sample in samples:
        class_name = rng.choice(CLASS_NAMES)
        gt_x, gt_y, gt_w, gt_h = _box(sample.width, sample.height, 0.2, 0.2)
        pred_x, pred_y, pred_w, pred_h = _box(sample.width, sample.height, 0.3, 0.3)
        object_detection_gt.append(
            CreateObjectDetection(
                class_name=class_name, x=gt_x, y=gt_y, width=gt_w, height=gt_h
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )
        object_detection_pred.append(
            CreateObjectDetection(
                class_name=class_name,
                x=pred_x,
                y=pred_y,
                width=pred_w,
                height=pred_h,
                confidence=rng.uniform(0.5, 1.0),
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=object_detection_gt,
        collection_name=OBJECT_DETECTION_GT_SOURCE,
    )
    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=object_detection_pred,
        collection_name=OBJECT_DETECTION_PRED_SOURCE,
    )

    # --- Classification sources: one GT and one prediction label per image. ---
    classification_gt = []
    classification_pred = []
    for sample in samples:
        classification_gt.append(
            CreateClassification(class_name=rng.choice(CLASS_NAMES)).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )
        classification_pred.append(
            CreateClassification(
                class_name=rng.choice(CLASS_NAMES),
                confidence=rng.uniform(0.5, 1.0),
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=classification_gt,
        collection_name=CLASSIFICATION_GT_SOURCE,
    )
    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=classification_pred,
        collection_name=CLASSIFICATION_PRED_SOURCE,
    )

    # --- Semantic-segmentation sources: a rectangle per image; the prediction
    #     rectangle is shifted so GT and prediction partially overlap. ---
    segmentation_gt = []
    segmentation_pred = []
    for sample in samples:
        class_name = rng.choice(CLASS_NAMES)
        gt_mask = _rectangle_mask(sample.width, sample.height, 0.2, 0.2)
        pred_mask = _rectangle_mask(sample.width, sample.height, 0.3, 0.3)
        segmentation_gt.append(
            CreateSegmentationMask.from_binary_mask(
                class_name=class_name,
                binary_mask=gt_mask,
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )
        segmentation_pred.append(
            CreateSegmentationMask.from_binary_mask(
                class_name=class_name,
                binary_mask=pred_mask,
                confidence=rng.uniform(0.5, 1.0),
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=segmentation_gt,
        collection_name=SEGMENTATION_GT_SOURCE,
    )
    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=segmentation_pred,
        collection_name=SEGMENTATION_PRED_SOURCE,
    )

    print(
        f"Created dataset '{DATASET_NAME}' with {len(samples)} images and gt/pred sources for "
        "object detection, classification, and semantic segmentation."
    )
    ls.start_gui()


if __name__ == "__main__":
    main()
