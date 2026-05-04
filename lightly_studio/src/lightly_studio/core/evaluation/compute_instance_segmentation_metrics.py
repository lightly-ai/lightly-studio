"""Instance-segmentation metrics with class-aware greedy matching."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox


@dataclass
class InstanceSegmentationAnnotation:
    """Flattened instance-segmentation annotation."""

    annotation_id: UUID
    sample_id: UUID
    label_id: UUID
    confidence: float
    image_width: int
    image_height: int
    x: int
    y: int
    width: int
    height: int
    segmentation_mask: list[int]


@dataclass
class MatchRecord:
    """One row in the per-annotation match table."""

    sample_id: UUID
    pred_id: UUID | None
    gt_id: UUID | None
    iou: float | None
    match_type: str
    label_id: UUID


def match_annotations(
    gt: list[InstanceSegmentationAnnotation],
    pred: list[InstanceSegmentationAnnotation],
    iou_threshold: float,
    confidence_threshold: float,
) -> list[MatchRecord]:
    """Match predicted masks to GT masks across all images."""
    gt_by_image: dict[UUID, list[InstanceSegmentationAnnotation]] = defaultdict(list)
    for annotation in gt:
        gt_by_image[annotation.sample_id].append(annotation)

    pred_by_image: dict[UUID, list[InstanceSegmentationAnnotation]] = defaultdict(list)
    for annotation in pred:
        pred_by_image[annotation.sample_id].append(annotation)

    records: list[MatchRecord] = []
    for sample_id in gt_by_image.keys() | pred_by_image.keys():
        records.extend(
            _match_single_image(
                sample_id=sample_id,
                image_gt=gt_by_image[sample_id],
                image_pred=pred_by_image[sample_id],
                iou_threshold=iou_threshold,
                confidence_threshold=confidence_threshold,
            )
        )
    return records


def compute_metrics(
    matches: list[MatchRecord],
    pred_confidences: dict[UUID, float],
    label_names: dict[UUID, str],
) -> dict:
    """Compute instance-segmentation metrics from match records."""
    tp = sum(1 for match in matches if match.match_type == "TP")
    fp = sum(1 for match in matches if match.match_type == "FP")
    fn = sum(1 for match in matches if match.match_type == "FN")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    pred_records_by_label: dict[UUID, list[tuple[float, bool]]] = defaultdict(list)
    for match in matches:
        if match.pred_id is None:
            continue
        pred_records_by_label[match.label_id].append(
            (pred_confidences.get(match.pred_id, 0.0), match.match_type == "TP")
        )

    gt_count_by_label: dict[UUID, int] = defaultdict(int)
    for match in matches:
        if match.match_type in ("TP", "FN"):
            gt_count_by_label[match.label_id] += 1

    per_class_metrics: dict[str, dict] = {}
    ap_values: list[float] = []
    for label_id in pred_records_by_label.keys() | gt_count_by_label.keys():
        sorted_preds = sorted(
            pred_records_by_label[label_id],
            key=lambda item: item[0],
            reverse=True,
        )
        tp_flags = [is_tp for _, is_tp in sorted_preds]
        total_gt = gt_count_by_label[label_id]

        ap = _compute_ap(tp_flags, total_gt)
        ap_values.append(ap)

        class_tp = sum(tp_flags)
        class_fp = len(tp_flags) - class_tp
        class_fn = total_gt - class_tp

        class_precision = class_tp / (class_tp + class_fp) if (class_tp + class_fp) > 0 else 0.0
        class_recall = class_tp / (class_tp + class_fn) if (class_tp + class_fn) > 0 else 0.0
        class_f1 = (
            2 * class_precision * class_recall / (class_precision + class_recall)
            if (class_precision + class_recall) > 0
            else 0.0
        )

        per_class_metrics[label_names.get(label_id, str(label_id))] = {
            "ap": round(ap, 4),
            "precision": round(class_precision, 4),
            "recall": round(class_recall, 4),
            "f1": round(class_f1, 4),
        }

    mean_ap = float(np.mean(ap_values)) if ap_values else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP": round(mean_ap, 4),
        "per_class_metrics": per_class_metrics,
    }


def _match_single_image(
    sample_id: UUID,
    image_gt: list[InstanceSegmentationAnnotation],
    image_pred: list[InstanceSegmentationAnnotation],
    iou_threshold: float,
    confidence_threshold: float,
) -> list[MatchRecord]:
    records: list[MatchRecord] = []
    matched_gt: set[UUID] = set()
    mask_cache: dict[UUID, np.ndarray] = {}

    for pred_annotation in sorted(
        image_pred,
        key=lambda annotation: annotation.confidence,
        reverse=True,
    ):
        if pred_annotation.confidence < confidence_threshold:
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_annotation.annotation_id,
                    gt_id=None,
                    iou=None,
                    match_type="FP",
                    label_id=pred_annotation.label_id,
                )
            )
            continue

        best_iou = iou_threshold - 1e-9
        best_gt: InstanceSegmentationAnnotation | None = None
        pred_mask = _get_binary_mask(pred_annotation, mask_cache)
        for gt_annotation in image_gt:
            if (
                gt_annotation.annotation_id in matched_gt
                or gt_annotation.label_id != pred_annotation.label_id
            ):
                continue
            gt_mask = _get_binary_mask(gt_annotation, mask_cache)
            iou = _mask_iou(pred_mask, gt_mask)
            if iou > best_iou:
                best_iou = iou
                best_gt = gt_annotation

        if best_gt is not None:
            matched_gt.add(best_gt.annotation_id)
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_annotation.annotation_id,
                    gt_id=best_gt.annotation_id,
                    iou=round(best_iou, 4),
                    match_type="TP",
                    label_id=pred_annotation.label_id,
                )
            )
        else:
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_annotation.annotation_id,
                    gt_id=None,
                    iou=None,
                    match_type="FP",
                    label_id=pred_annotation.label_id,
                )
            )

    for gt_annotation in image_gt:
        if gt_annotation.annotation_id in matched_gt:
            continue
        records.append(
            MatchRecord(
                sample_id=sample_id,
                pred_id=None,
                gt_id=gt_annotation.annotation_id,
                iou=None,
                match_type="FN",
                label_id=gt_annotation.label_id,
            )
        )

    return records


def _get_binary_mask(
    annotation: InstanceSegmentationAnnotation,
    mask_cache: dict[UUID, np.ndarray],
) -> np.ndarray:
    cached = mask_cache.get(annotation.annotation_id)
    if cached is not None:
        return cached

    bounding_box = BoundingBox(
        xmin=annotation.x,
        ymin=annotation.y,
        xmax=annotation.x + annotation.width,
        ymax=annotation.y + annotation.height,
    )
    segmentation = BinaryMaskSegmentation.from_rle(
        rle_row_wise=annotation.segmentation_mask,
        width=annotation.image_width,
        height=annotation.image_height,
        bounding_box=bounding_box,
    )
    binary_mask = segmentation.get_binary_mask().astype(bool)
    mask_cache[annotation.annotation_id] = binary_mask
    return binary_mask


def _mask_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return float(intersection / union) if union > 0 else 0.0


def _compute_ap(tp_flags: list[bool], total_gt: int) -> float:
    if total_gt == 0 or not tp_flags:
        return 0.0

    cum_tp = 0
    cum_fp = 0
    precisions: list[float] = []
    recalls: list[float] = []
    for is_tp in tp_flags:
        if is_tp:
            cum_tp += 1
        else:
            cum_fp += 1
        precisions.append(cum_tp / (cum_tp + cum_fp))
        recalls.append(cum_tp / total_gt)

    ap = 0.0
    for threshold in np.linspace(0, 1, 101):
        precision_at_recall = [p for p, r in zip(precisions, recalls) if r >= threshold]
        ap += max(precision_at_recall) if precision_at_recall else 0.0
    return ap / 101
