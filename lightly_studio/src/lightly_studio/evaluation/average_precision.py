"""Compute detection mean average precision by re-matching at several IoU thresholds.

Average precision needs the full precision-recall curve, so it re-matches the
stored predictions and ground truths instead of reading the single-threshold
metrics. The IoU matrix is computed once per class per image and reused across
thresholds, as ``object_detection_metric`` is split for.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np

from lightly_studio.evaluation.object_detection_metric import (
    BoundingBox,
    compute_iou_matrix,
    match_with_iou_matrix,
    to_corner_array,
)
from lightly_studio.models.evaluation_metrics import (
    ClassAveragePrecision,
    DetectionAveragePrecision,
)

# COCO uses a 101-point recall grid for the precision-recall integral.
_RECALL_GRID = np.linspace(0.0, 1.0, 101)

# COCO averages average precision over IoU 0.50, 0.55, ..., 0.95.
COCO_IOU_THRESHOLDS = [round(0.5 + 0.05 * step, 2) for step in range(10)]


def compute(
    gt_per_image: Sequence[Sequence[BoundingBox]],
    pred_per_image: Sequence[Sequence[BoundingBox]],
    label_names: dict[UUID, str],
    iou_thresholds: Sequence[float],
) -> DetectionAveragePrecision:
    """Compute per-class and mean average precision over the IoU thresholds.

    Only classes present in the ground truth are scored. For each such class the
    average precision is the mean over the thresholds of the 101-point
    interpolated precision-recall integral. The mean average precision is the
    mean of the per-class values.

    Args:
        gt_per_image: Ground-truth boxes per image.
        pred_per_image: Predicted boxes per image (with confidence).
        label_names: Mapping from label ID to label name.
        iou_thresholds: IoU thresholds to average over.

    Returns:
        The per-class and mean average precision.
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
            iou_matrix = compute_iou_matrix(
                pred_corners=to_corner_array(class_predictions),
                gt_corners=to_corner_array(class_ground_truths),
            )
            for threshold in iou_thresholds:
                result = match_with_iou_matrix(
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
        (label for label, count in ground_truth_count.items() if count > 0),
        key=lambda label: label_names[label],
    )
    per_class = [
        ClassAveragePrecision(
            label=label_names[label],
            average_precision=float(
                np.mean(
                    [
                        _average_precision(
                            records=scored.get((label, threshold), []),
                            ground_truth_count=ground_truth_count[label],
                        )
                        for threshold in iou_thresholds
                    ]
                )
            ),
        )
        for label in scored_labels
    ]
    mean_average_precision = (
        float(np.mean([entry.average_precision for entry in per_class])) if per_class else 0.0
    )
    return DetectionAveragePrecision(
        mean_average_precision=mean_average_precision,
        per_class=per_class,
        iou_thresholds=list(iou_thresholds),
    )


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
