"""Example: object detection and dummy classification evaluation runs."""

import random

import numpy as np
import numpy.typing as npt
from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.annotation import CreateClassification, CreateSegmentationMask
from lightly_studio.core.evaluation.register_gt_collection import (
    register_annotation_collection,
)
from lightly_studio.models.evaluation_result import EvaluationResultTable, EvaluationTaskType
from lightly_studio.resolvers import annotation_resolver

env = Env()
env.read_env()

gt_folder = ""
gt_json = ""
predictions_folder = (
    ""
)


def _add_random_classification_annotations(
    dataset: ls.ImageDataset,
    collection_name: str,
    *,
    is_ground_truth: bool,
    seed: int,
) -> None:
    """Create one random single-label classification annotation per sample."""
    rng = random.Random(seed)
    labels = ["cat", "dog"]

    annotations = []
    for sample in dataset:
        label = rng.choice(labels)
        confidence = None if is_ground_truth else rng.uniform(0.5, 1.0)
        annotations.append(
            CreateClassification(label=label, confidence=confidence).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=annotations,
        collection_name=collection_name,
    )
    register_annotation_collection(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
        root_collection_id=dataset.collection_id,
        collection_name=collection_name,
        is_ground_truth=is_ground_truth,
    )


def _add_random_instance_segmentation_annotations(
    dataset: ls.ImageDataset,
    collection_name: str,
    *,
    is_ground_truth: bool,
    seed: int,
) -> None:
    """Create one random rectangular instance mask per sample."""
    rng = random.Random(seed)
    labels = ["cat", "dog"]

    annotations = []
    for sample in dataset:
        label = rng.choice(labels)
        confidence = None if is_ground_truth else rng.uniform(0.5, 1.0)
        binary_mask = _make_random_rectangle_mask(
            width=sample.width,
            height=sample.height,
            rng=rng,
        )
        annotations.append(
            CreateSegmentationMask.from_binary_mask(
                label=label,
                binary_mask=binary_mask,
                confidence=confidence,
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=annotations,
        collection_name=collection_name,
    )
    register_annotation_collection(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
        root_collection_id=dataset.collection_id,
        collection_name=collection_name,
        is_ground_truth=is_ground_truth,
    )


def _make_random_rectangle_mask(
    width: int,
    height: int,
    rng: random.Random,
) -> npt.NDArray[np.int_]:
    """Create a simple rectangular binary mask inside one image."""
    rect_width = max(width // 5, 1)
    rect_height = max(height // 5, 1)
    x0 = rng.randint(0, max(width - rect_width, 0))
    y0 = rng.randint(0, max(height - rect_height, 0))
    x1 = min(x0 + rect_width, width)
    y1 = min(y0 + rect_height, height)

    binary_mask = np.zeros((height, width), dtype=int)
    binary_mask[y0:y1, x0:x1] = 1
    return binary_mask


def _print_metrics(result: EvaluationResultTable) -> None:
    for subset_name, metrics in result.metrics.items():
        if "accuracy" in metrics:
            print(
                f"{subset_name:12s} | "
                f"Acc={metrics['accuracy']:.3f}  "
                f"P={metrics['precision']:.3f}  "
                f"R={metrics['recall']:.3f}  "
                f"F1={metrics['f1']:.3f}"
            )
        else:
            print(
                f"{subset_name:12s} | "
                f"mAP={metrics['mAP']:.3f}  "
                f"P={metrics['precision']:.3f}  "
                f"R={metrics['recall']:.3f}  "
                f"F1={metrics['f1']:.3f}"
            )


db_manager.connect(cleanup_existing=True)

# 1. Load images with ground-truth annotations (COCO format).
dataset = ls.ImageDataset.create()

dataset.add_samples_from_coco(
    annotations_json=gt_json,
    images_path=gt_folder,
    annotation_collection="ground_truth",
    is_ground_truth=True,
)

# 2. Load predictions from one or more models (Lightly format).
#    Confidence scores are read from the ``score`` field in each annotation JSON file.
#
#    Each collection name becomes one attachable evaluation run in the backend/frontend.
#    Replace the folder paths below with actual prediction exports when comparing models.
prediction_runs = [
    {
        "input_folder": predictions_folder,
        "collection_name": "YOLOv8-n epoch 50",
    },
    {
        "input_folder": predictions_folder,
        "collection_name": "YOLOv8-XL epoch 50",
    },
]

for prediction_run in prediction_runs:
    dataset.add_predictions_from_lightly(
        input_folder=prediction_run["input_folder"],
        collection_name=prediction_run["collection_name"],
    )

# 3. Compute evaluation metrics.
#
# Metrics are computed for the evaluated sample snapshot stored with each run.
results = [
    dataset.evaluate(
        name=prediction_run["collection_name"],
        gt_collection="ground_truth",
        prediction_collection=prediction_run["collection_name"],
        iou_threshold=0.5,
        confidence_threshold=0.0,
    )
    for prediction_run in prediction_runs
]

# 4. Inspect results.
for prediction_run, result in zip(prediction_runs, results):
    print(f"\n=== {prediction_run['collection_name']} ===")
    _print_metrics(result)

# 5. Add dummy classification GT/prediction collections through the Python API.
#
#    This is a minimal verification example for the new classification evaluation path.
_add_random_classification_annotations(
    dataset,
    collection_name="classification_ground_truth",
    is_ground_truth=True,
    seed=7,
)
_add_random_classification_annotations(
    dataset,
    collection_name="classification_predictions",
    is_ground_truth=False,
    seed=11,
)

classification_result = dataset.evaluate(
    name="Dummy classification",
    gt_collection="classification_ground_truth",
    prediction_collection="classification_predictions",
    task_type=EvaluationTaskType.CLASSIFICATION,
)

print("\n=== Dummy classification ===")
_print_metrics(classification_result)

# 6. Add dummy instance-segmentation GT/prediction collections through the Python API.
#
#    Masks are simple random rectangles to verify the new segmentation evaluation path.
_add_random_instance_segmentation_annotations(
    dataset,
    collection_name="segmentation_ground_truth",
    is_ground_truth=True,
    seed=13,
)
_add_random_instance_segmentation_annotations(
    dataset,
    collection_name="segmentation_predictions",
    is_ground_truth=False,
    seed=17,
)

segmentation_result = dataset.evaluate(
    name="Dummy instance segmentation",
    gt_collection="segmentation_ground_truth",
    prediction_collection="segmentation_predictions",
    task_type=EvaluationTaskType.INSTANCE_SEGMENTATION,
)

print("\n=== Dummy instance segmentation ===")
_print_metrics(segmentation_result)

ls.start_gui()
