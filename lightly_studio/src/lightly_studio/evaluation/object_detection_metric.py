"""Object detection evaluation metric primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


@dataclass
class BoundingBox:
    """A bounding box annotation in [x, y, width, height] format.

    Attributes:
        annotation_id: Unique identifier, used to map results back to source annotations.
        x: Left edge coordinate.
        y: Top edge coordinate.
        width: Box width.
        height: Box height.
        label_id: Class label ID.
        confidence: Prediction confidence score. None for ground truth annotations.
    """

    annotation_id: UUID
    x: int
    y: int
    width: int
    height: int
    label_id: UUID
    confidence: float | None = None


@dataclass
class DetectionMatch:
    """A matched prediction-GT pair (TP).

    Attributes:
        pred_id: ID of the matched prediction.
        gt_id: ID of the matched ground truth.
        iou: IoU between the matched boxes.
    """

    pred_id: UUID
    gt_id: UUID
    iou: float


@dataclass
class MatchingResult:
    """Full matching result at a fixed IoU threshold.

    Attributes:
        matches: TP pairs with their IoU values.
        unmatched_prediction_ids: IDs of FP predictions.
        unmatched_gt_ids: IDs of FN ground truths.
    """

    matches: list[DetectionMatch] = field(default_factory=list)
    unmatched_prediction_ids: list[UUID] = field(default_factory=list)
    unmatched_gt_ids: list[UUID] = field(default_factory=list)

    @property
    def tp(self) -> int:
        """Number of true positive detections."""
        return len(self.matches)

    @property
    def fp(self) -> int:
        """Number of false positive detections."""
        return len(self.unmatched_prediction_ids)

    @property
    def fn(self) -> int:
        """Number of false negatives (missed ground truths)."""
        return len(self.unmatched_gt_ids)

    def extend(self, other: MatchingResult) -> None:
        """Extend this result with another matching result.

        Args:
            other: Another matching result to merge into this one.
        """
        self.matches.extend(other.matches)
        self.unmatched_prediction_ids.extend(other.unmatched_prediction_ids)
        self.unmatched_gt_ids.extend(other.unmatched_gt_ids)


def match_image(
    predictions: list[BoundingBox],
    ground_truths: list[BoundingBox],
    iou_threshold: float,
    classwise: bool,
) -> MatchingResult:
    """Match predictions to ground truths for a single image.

    Args:
        predictions: All predicted bounding boxes for the image.
        ground_truths: All ground truth bounding boxes for the image.
        iou_threshold: Minimum IoU for a prediction to count as a TP.
        classwise: If True, predictions and ground truths are only matched within
            the same class. If False, matching is done globally across all classes.

    Returns:
        Per-image matching result.
    """
    if classwise:
        all_labels = {b.label_id for b in predictions} | {b.label_id for b in ground_truths}
        result = MatchingResult()
        for label in all_labels:
            class_predictions = [b for b in predictions if b.label_id == label]
            class_gts = [b for b in ground_truths if b.label_id == label]
            result.extend(
                match_with_iou_matrix(
                    predictions=class_predictions,
                    ground_truths=class_gts,
                    iou_matrix=compute_iou_matrix(
                        pred_corners=to_corner_array(class_predictions),
                        gt_corners=to_corner_array(class_gts),
                    ),
                    iou_threshold=iou_threshold,
                )
            )
        return result
    return match_with_iou_matrix(
        predictions=predictions,
        ground_truths=ground_truths,
        iou_matrix=compute_iou_matrix(
            pred_corners=to_corner_array(predictions),
            gt_corners=to_corner_array(ground_truths),
        ),
        iou_threshold=iou_threshold,
    )


def match_with_iou_matrix(
    predictions: Sequence[BoundingBox],
    ground_truths: Sequence[BoundingBox],
    iou_matrix: NDArray[np.float64],
    iou_threshold: float,
) -> MatchingResult:
    """Run greedy matching given a pre-computed IoU matrix.

    Separating matching from IoU computation allows reuse across multiple IoU
    thresholds (e.g. COCO mAP sweep) without recomputing the matrix.

    Args:
        predictions: Predicted bounding boxes.
        ground_truths: Ground truth bounding boxes.
        iou_matrix: Pairwise IoU of shape (len(predictions), len(ground_truths)).
        iou_threshold: Minimum IoU for a prediction to count as a TP.

    Returns:
        Matching result with TP pairs, FP prediction IDs, and FN ground truth IDs.

    Note:
        No class-label filtering is applied. Callers are responsible for
        ensuring that ``predictions`` and ``ground_truths`` belong to the same
        class if strict class-wise matching is required.
    """
    if iou_matrix.shape != (len(predictions), len(ground_truths)):
        raise ValueError(
            f"iou_matrix shape {iou_matrix.shape} does not match "
            f"(len(predictions)={len(predictions)}, len(ground_truths)={len(ground_truths)})"
        )
    if not predictions and not ground_truths:
        return MatchingResult()
    if not predictions:
        return MatchingResult(
            unmatched_gt_ids=[gt.annotation_id for gt in ground_truths],
        )
    if not ground_truths:
        return MatchingResult(
            unmatched_prediction_ids=[p.annotation_id for p in predictions],
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
                    pred_id=predictions[pred_idx].annotation_id,
                    gt_id=ground_truths[best_gt_idx].annotation_id,
                    iou=best_iou,
                )
            )

    return MatchingResult(
        matches=matches,
        unmatched_prediction_ids=[
            p.annotation_id for i, p in enumerate(predictions) if i not in matched_pred
        ],
        unmatched_gt_ids=[
            gt.annotation_id for i, gt in enumerate(ground_truths) if i not in matched_gt
        ],
    )


def compute_iou_matrix(
    pred_corners: NDArray[np.int64],
    gt_corners: NDArray[np.int64],
) -> NDArray[np.float64]:
    """Compute pairwise IoU from corner arrays.

    Args:
        pred_corners: (P, 4) array of [x1, y1, x2, y2] prediction boxes in image pixel coordinates.
        gt_corners: (G, 4) array of [x1, y1, x2, y2] ground-truth boxes in image pixel coordinates.

    Returns:
        IoU matrix of shape (P, G), or an empty array if either input is empty.
    """
    if pred_corners.size == 0 or gt_corners.size == 0:
        return np.empty((len(pred_corners), len(gt_corners)), dtype=np.float64)

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

    iou = inter / union
    return np.asarray(np.nan_to_num(iou, nan=0.0), dtype=np.float64)  # (P, G)


def to_corner_array(boxes: Sequence[BoundingBox]) -> NDArray[np.int64]:
    """Convert bounding boxes to [x1, y1, x2, y2] corner format.

    Args:
        boxes: Bounding boxes in [x, y, width, height] format.

    Returns:
        (N, 4) array of [x1, y1, x2, y2] corner coordinates.
    """
    if not boxes:
        return np.empty((0, 4), dtype=np.int64)
    return np.array(
        [[b.x, b.y, b.x + b.width, b.y + b.height] for b in boxes],
        dtype=np.int64,
    )
