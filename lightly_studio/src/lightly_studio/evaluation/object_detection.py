"""Object detection evaluation primitives.

Core data types and pure-computation functions for matching predictions to ground
truths at a fixed IoU threshold. DB loading and orchestration live in
object_detection_evaluation.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import numpy as np


@dataclass
class BoundingBox:
    """A bounding box annotation in [x, y, width, height] format.

    Attributes:
        uuid: Unique identifier, used to map results back to source annotations.
        x: Left edge coordinate.
        y: Top edge coordinate.
        width: Box width.
        height: Box height.
        label: Class label ID.
        confidence: Prediction confidence score. None for ground truth annotations.
    """

    uuid: UUID
    x: float
    y: float
    width: float
    height: float
    label: UUID
    confidence: float | None = None


@dataclass
class DetectionMatch:
    """A matched prediction-GT pair (TP).

    Attributes:
        pred_uuid: UUID of the matched prediction.
        gt_uuid: UUID of the matched ground truth.
        iou: IoU between the matched boxes.
    """

    pred_uuid: UUID
    gt_uuid: UUID
    iou: float


@dataclass
class ImageMatchingResult:
    """Full per-image matching result at a fixed IoU threshold.

    Attributes:
        sample_id: Identifier for the image.
        matches: TP pairs with their IoU values.
        unmatched_prediction_uuids: UUIDs of FP predictions.
        unmatched_gt_uuids: UUIDs of FN ground truths.
    """

    sample_id: UUID
    matches: list[DetectionMatch] = field(default_factory=list)
    unmatched_prediction_uuids: list[UUID] = field(default_factory=list)
    unmatched_gt_uuids: list[UUID] = field(default_factory=list)

    @property
    def tp(self) -> int:
        """Number of true positive detections."""
        return len(self.matches)

    @property
    def fp(self) -> int:
        """Number of false positive detections."""
        return len(self.unmatched_prediction_uuids)

    @property
    def fn(self) -> int:
        """Number of false negatives (missed ground truths)."""
        return len(self.unmatched_gt_uuids)


def match_image(
    sample_id: UUID,
    predictions: list[BoundingBox],
    ground_truths: list[BoundingBox],
    *,
    iou_threshold: float,
    classwise: bool,
) -> ImageMatchingResult:
    """Match predictions to ground truths for a single image.

    Args:
        sample_id: Identifier for the image.
        predictions: All predicted bounding boxes for the image.
        ground_truths: All ground truth bounding boxes for the image.
        iou_threshold: Minimum IoU for a prediction to count as a TP.
        classwise: If True, predictions and ground truths are only matched within
            the same class. If False, matching is done globally across all classes.

    Returns:
        Per-image matching result.
    """
    if classwise:
        all_labels = {b.label for b in predictions} | {b.label for b in ground_truths}
        matches: list[DetectionMatch] = []
        unmatched_pred_uuids: list[UUID] = []
        unmatched_gt_uuids: list[UUID] = []
        for label in all_labels:
            class_predictions = [b for b in predictions if b.label == label]
            class_gts = [b for b in ground_truths if b.label == label]
            result = match_with_iou_matrix(
                sample_id=sample_id,
                predictions=class_predictions,
                ground_truths=class_gts,
                iou_matrix=compute_iou_matrix(
                    pred_corners=to_corner_array(class_predictions),
                    gt_corners=to_corner_array(class_gts),
                ),
                iou_threshold=iou_threshold,
            )
            matches.extend(result.matches)
            unmatched_pred_uuids.extend(result.unmatched_prediction_uuids)
            unmatched_gt_uuids.extend(result.unmatched_gt_uuids)
        return ImageMatchingResult(
            sample_id=sample_id,
            matches=matches,
            unmatched_prediction_uuids=unmatched_pred_uuids,
            unmatched_gt_uuids=unmatched_gt_uuids,
        )
    return match_with_iou_matrix(
        sample_id=sample_id,
        predictions=predictions,
        ground_truths=ground_truths,
        iou_matrix=compute_iou_matrix(
            pred_corners=to_corner_array(predictions),
            gt_corners=to_corner_array(ground_truths),
        ),
        iou_threshold=iou_threshold,
    )


def match_with_iou_matrix(
    sample_id: UUID,
    predictions: list[BoundingBox],
    ground_truths: list[BoundingBox],
    iou_matrix: np.ndarray,
    *,
    iou_threshold: float,
) -> ImageMatchingResult:
    """Run greedy matching given a pre-computed IoU matrix.

    Separating matching from IoU computation allows reuse across multiple IoU
    thresholds (e.g. COCO mAP sweep) without recomputing the matrix.

    Args:
        sample_id: Identifier for the image.
        predictions: Predicted bounding boxes.
        ground_truths: Ground truth bounding boxes.
        iou_matrix: Pairwise IoU of shape (len(predictions), len(ground_truths)).
        iou_threshold: Minimum IoU for a prediction to count as a TP.

    Returns:
        Per-image matching result.
    """
    if not predictions and not ground_truths:
        return ImageMatchingResult(sample_id=sample_id)
    if not predictions:
        return ImageMatchingResult(
            sample_id=sample_id,
            unmatched_gt_uuids=[gt.uuid for gt in ground_truths],
        )
    if not ground_truths:
        return ImageMatchingResult(
            sample_id=sample_id,
            unmatched_prediction_uuids=[p.uuid for p in predictions],
        )

    confidence_order = sorted(
        range(len(predictions)),
        key=lambda i: predictions[i].confidence or 0.0,
        reverse=True,
    )

    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    matches: list[DetectionMatch] = []

    for pred_idx in confidence_order:
        pred = predictions[pred_idx]
        best_iou = -1.0
        best_gt_idx = -1
        for gt_idx in range(len(ground_truths)):
            if gt_idx in matched_gt:
                continue
            iou = float(iou_matrix[pred_idx, gt_idx])
            if iou >= iou_threshold and iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx
        if best_gt_idx >= 0:
            matched_gt.add(best_gt_idx)
            matched_pred.add(pred_idx)
            matches.append(
                DetectionMatch(
                    pred_uuid=pred.uuid,
                    gt_uuid=ground_truths[best_gt_idx].uuid,
                    iou=best_iou,
                )
            )

    return ImageMatchingResult(
        sample_id=sample_id,
        matches=matches,
        unmatched_prediction_uuids=[
            p.uuid for i, p in enumerate(predictions) if i not in matched_pred
        ],
        unmatched_gt_uuids=[gt.uuid for i, gt in enumerate(ground_truths) if i not in matched_gt],
    )


def to_corner_array(boxes: list[BoundingBox]) -> np.ndarray:
    """Convert bounding boxes to an (N, 4) array of [x1, y1, x2, y2] corners."""
    return np.array([[b.x, b.y, b.x + b.width, b.y + b.height] for b in boxes])


def compute_iou_matrix(pred_corners: np.ndarray, gt_corners: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU from corner arrays.

    Args:
        pred_corners: Array of shape (P, 4) with [x1, y1, x2, y2] per prediction.
        gt_corners: Array of shape (G, 4) with [x1, y1, x2, y2] per ground truth.

    Returns:
        IoU matrix of shape (P, G), or an empty array if either input is empty.
    """
    if pred_corners.size == 0 or gt_corners.size == 0:
        return np.empty((len(pred_corners), len(gt_corners)))

    inter_x1 = np.maximum(pred_corners[:, None, 0], gt_corners[None, :, 0])
    inter_y1 = np.maximum(pred_corners[:, None, 1], gt_corners[None, :, 1])
    inter_x2 = np.minimum(pred_corners[:, None, 2], gt_corners[None, :, 2])
    inter_y2 = np.minimum(pred_corners[:, None, 3], gt_corners[None, :, 3])

    inter = np.maximum(0, inter_x2 - inter_x1) * np.maximum(0, inter_y2 - inter_y1)
    pred_area = (pred_corners[:, 2] - pred_corners[:, 0]) * (
        pred_corners[:, 3] - pred_corners[:, 1]
    )
    gt_area = (gt_corners[:, 2] - gt_corners[:, 0]) * (gt_corners[:, 3] - gt_corners[:, 1])
    union = pred_area[:, None] + gt_area[None, :] - inter

    return inter / union  # (P, G)
