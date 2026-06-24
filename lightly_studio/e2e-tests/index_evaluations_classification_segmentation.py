"""Index a dataset with synthetic classification and semantic-segmentation sources.

Use this to exercise the GUI evaluation trigger for the classification and
semantic-segmentation task types: it creates ``gt``/``pred`` annotation sources
for both tasks on a single dataset, then launches the UI so you can open the
Evaluation panel and start runs.

Annotations are synthetic, so the only input required is an images folder
(segmentation masks are generated to match each image's dimensions). Point it at
any images you already have via ``EXAMPLES_IMAGES_PATH`` (defaults to the COCO
subset used by ``index_evaluations.py``).

Note: ``cleanup_existing`` defaults to ``False`` so this dataset is added next to
any existing data. Set it to ``True`` if you want a fresh database.
"""

import random

import numpy as np
from environs import Env
from numpy.typing import NDArray

import lightly_studio as ls
from lightly_studio.core.annotation.annotation_create import (
    CreateClassification,
    CreateSegmentationMask,
)
from lightly_studio.database import db_manager
from lightly_studio.resolvers import annotation_resolver

env = Env()
env.read_env()

IMAGES_PATH = env.path("EXAMPLES_IMAGES_PATH", "datasets/coco_subset_128_images/images")

DATASET_NAME = "evaluation_classification_segmentation_dataset"
CLASS_NAMES = ["cat", "dog", "bird"]
RANDOM_SEED = 42

CLASSIFICATION_GT_SOURCE = "classification_gt"
CLASSIFICATION_PRED_SOURCE = "classification_pred"
SEGMENTATION_GT_SOURCE = "segmentation_gt"
SEGMENTATION_PRED_SOURCE = "segmentation_pred"


def _rectangle_mask(
    width: int,
    height: int,
    left_fraction: float,
    top_fraction: float,
) -> NDArray[np.int_]:
    """Return a binary mask (height x width) with a filled rectangle."""
    mask = np.zeros((height, width), dtype=np.int_)
    x0 = int(width * left_fraction)
    y0 = int(height * top_fraction)
    x1 = min(width, x0 + max(1, width // 2))
    y1 = min(height, y0 + max(1, height // 2))
    mask[y0:y1, x0:x1] = 1
    return mask


def main() -> None:
    """Create the dataset, synthesize sources, and launch the UI."""
    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=False)

    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    samples = list(dataset)
    rng = random.Random(RANDOM_SEED)

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
        f"Created dataset '{DATASET_NAME}' with {len(samples)} images and sources: "
        f"{CLASSIFICATION_GT_SOURCE}, {CLASSIFICATION_PRED_SOURCE}, "
        f"{SEGMENTATION_GT_SOURCE}, {SEGMENTATION_PRED_SOURCE}."
    )
    ls.start_gui()


if __name__ == "__main__":
    main()
