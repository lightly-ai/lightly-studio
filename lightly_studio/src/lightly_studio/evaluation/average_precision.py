"""Compute and persist per-class detection average precision at several IoU thresholds.

Average precision needs the full precision-recall curve, so it re-matches the
stored predictions and ground truths instead of reading the single-threshold
metrics. The IoU matrix is computed once per class per image and reused across
thresholds, as ``object_detection_metric`` is split for. Only the per-class value at
each threshold is persisted. Means over classes or thresholds are derived on read.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from sqlmodel import Session

from lightly_studio.evaluation import object_detection_metric
from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.evaluation.object_detection_metric import BoundingBox
from lightly_studio.models.evaluation_class_metric import (
    EvaluationClassMetricCreate,
    EvaluationClassMetricTable,
)
from lightly_studio.resolvers import evaluation_class_metric_resolver

# COCO averages average precision over IoU 0.50, 0.55, ..., 0.95.
COCO_IOU_THRESHOLDS = [round(0.5 + 0.05 * step, 2) for step in range(10)]

# COCO uses a 101-point recall grid for the precision-recall integral.
_RECALL_GRID = np.linspace(0.0, 1.0, 101)

# Class metric name of the average precision. The IoU threshold is in the config override.
METRIC_NAME = "average_precision"


@dataclass(frozen=True)
class ClassAveragePrecision:
    """Average precision of one class at one IoU threshold.

    Attributes:
        label_id: Annotation label ID.
        iou_threshold: IoU threshold at which predictions count as true positives.
        average_precision: 101-point interpolated average precision in [0, 1].
    """

    label_id: UUID
    iou_threshold: float
    average_precision: float


def compute_for_run(data: EvaluationData) -> list[ClassAveragePrecision]:
    """Compute the per-class average precision of a run at the COCO IoU thresholds.

    Reads the loaded annotations, so call it before a commit expires them.

    Args:
        data: The run's selected samples and grouped ground-truth and prediction
            annotations.

    Returns:
        One entry per scored class and threshold.
    """
    sample_ids = sorted(data.selected_sample_ids)
    gt_per_image = [
        object_detection_metric.to_bounding_boxes(annotations=data.gt_per_sample.get(sample_id, []))
        for sample_id in sample_ids
    ]
    pred_per_image = [
        object_detection_metric.to_bounding_boxes(
            annotations=data.pred_per_sample.get(sample_id, [])
        )
        for sample_id in sample_ids
    ]
    return compute(
        gt_per_image=gt_per_image,
        pred_per_image=pred_per_image,
        iou_thresholds=COCO_IOU_THRESHOLDS,
    )


def persist(
    session: Session,
    evaluation_run_id: UUID,
    results: Sequence[ClassAveragePrecision],
    iou_threshold: float,
    classwise: bool,
) -> None:
    """Persist the per-class average precision of a run.

    Writes one row per result. The config override of a row holds the fields in which
    its matching differs from the run's config.

    Args:
        session: Database session.
        evaluation_run_id: ID of the run.
        results: The average precision per class and IoU threshold.
        iou_threshold: IoU threshold of the run's config.
        classwise: Class matching of the run's config.
    """
    evaluation_class_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=evaluation_run_id,
                annotation_label_id=result.label_id,
                metric_name=METRIC_NAME,
                config_override=config_override(
                    iou_threshold=result.iou_threshold,
                    run_iou_threshold=iou_threshold,
                    run_classwise=classwise,
                ),
                value=result.average_precision,
            )
            for result in results
        ],
    )


def by_label_and_threshold(
    class_metrics: Sequence[EvaluationClassMetricTable], run_config: dict[str, Any]
) -> dict[UUID, dict[float, float]]:
    """Group the stored average precision by label ID and IoU threshold.

    Args:
        class_metrics: The class metrics of one run. Rows of other metrics are ignored.
        run_config: The run's config. A row's IoU threshold is the one of the run's config
            with the row's config override applied.

    Returns:
        The average precision per IoU threshold, for every label with stored values.
    """
    grouped: dict[UUID, dict[float, float]] = {}
    for row in class_metrics:
        if row.metric_name == METRIC_NAME:
            threshold = float({**run_config, **row.config_override}["iou_threshold"])
            grouped.setdefault(row.annotation_label_id, {})[threshold] = row.value
    return grouped


def config_override(
    iou_threshold: float, run_iou_threshold: float, run_classwise: bool
) -> dict[str, Any]:
    """Return the config fields in which the matching at a threshold differs from the run.

    Average precision always matches predictions within their own class.

    Args:
        iou_threshold: IoU threshold of the average precision.
        run_iou_threshold: IoU threshold of the run's config.
        run_classwise: Class matching of the run's config.

    Returns:
        The differing fields. Empty if the matching is the same as the run's.
    """
    override: dict[str, Any] = {}
    if iou_threshold != run_iou_threshold:
        override["iou_threshold"] = iou_threshold
    if not run_classwise:
        override["classwise"] = True
    return override


def compute(
    gt_per_image: Sequence[Sequence[BoundingBox]],
    pred_per_image: Sequence[Sequence[BoundingBox]],
    iou_thresholds: Sequence[float],
) -> list[ClassAveragePrecision]:
    """Compute the average precision of each class at each IoU threshold.

    Only classes present in the ground truth are scored. Predictions are matched
    only within their own class, as in COCO.

    Args:
        gt_per_image: Ground-truth boxes per image.
        pred_per_image: Predicted boxes per image (with confidence).
        iou_thresholds: IoU thresholds to compute the average precision at.

    Returns:
        One entry per scored class and threshold, sorted by label ID and threshold.
    """
    ground_truth_count: dict[UUID, int] = {}
    # (label, threshold) -> list of (confidence, is_true_positive) across all images.
    scored: dict[tuple[UUID, float], list[tuple[float, bool]]] = {}

    for predictions, ground_truths in zip(pred_per_image, gt_per_image):
        labels = {box.label_id for box in predictions} | {box.label_id for box in ground_truths}
        for label in labels:
            class_predictions = [box for box in predictions if box.label_id == label]
            class_ground_truths = [box for box in ground_truths if box.label_id == label]
            ground_truth_count[label] = ground_truth_count.get(label, 0) + len(class_ground_truths)
            iou_matrix = object_detection_metric.compute_iou_matrix(
                pred_corners=object_detection_metric.to_corner_array(boxes=class_predictions),
                gt_corners=object_detection_metric.to_corner_array(boxes=class_ground_truths),
            )
            for threshold in iou_thresholds:
                result = object_detection_metric.match_with_iou_matrix(
                    predictions=class_predictions,
                    ground_truths=class_ground_truths,
                    iou_matrix=iou_matrix,
                    iou_threshold=threshold,
                )
                true_positive_ids = {match.pred_id for match in result.matches}
                scored.setdefault((label, threshold), []).extend(
                    (box.confidence or 0.0, box.annotation_id in true_positive_ids)
                    for box in class_predictions
                )

    scored_labels = sorted(
        (label for label, count in ground_truth_count.items() if count > 0), key=str
    )
    return [
        ClassAveragePrecision(
            label_id=label,
            iou_threshold=threshold,
            average_precision=_average_precision(
                records=scored.get((label, threshold), []),
                ground_truth_count=ground_truth_count[label],
            ),
        )
        for label in scored_labels
        for threshold in sorted(iou_thresholds)
    ]


def _average_precision(records: list[tuple[float, bool]], ground_truth_count: int) -> float:
    """Return the 101-point interpolated average precision for one class and threshold.

    Args:
        records: ``(confidence, is_true_positive)`` for every prediction of the class.
        ground_truth_count: Number of ground-truth boxes of the class.

    Returns:
        The average precision, or 0.0 when there is no ground truth.
    """
    if ground_truth_count == 0:
        return 0.0
    ranked = sorted(records, key=lambda record: record[0], reverse=True)
    true_positives = np.cumsum([1 if is_tp else 0 for _, is_tp in ranked])
    false_positives = np.cumsum([0 if is_tp else 1 for _, is_tp in ranked])
    recalls = true_positives / ground_truth_count
    precisions = true_positives / np.maximum(true_positives + false_positives, 1)
    interpolated = [
        precisions[recalls >= recall].max() if np.any(recalls >= recall) else 0.0
        for recall in _RECALL_GRID
    ]
    return float(np.mean(interpolated))
