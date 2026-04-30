"""Custom object detection metrics — no external eval libraries required."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

import numpy as np


@dataclass
class ODAnnotation:
    """Flattened annotation with bbox, used as input to the metrics engine."""

    annotation_id: UUID  # AnnotationBaseTable.sample_id (annotation PK)
    sample_id: UUID  # parent_sample_id (the image this annotation belongs to)
    label_id: UUID
    confidence: float
    x: int
    y: int
    w: int
    h: int


@dataclass
class MatchRecord:
    """One row in the per-annotation match table."""

    sample_id: UUID  # parent image
    pred_id: UUID | None  # annotation_id of prediction; None for FN
    gt_id: UUID | None  # annotation_id of GT; None for FP
    iou: float | None  # None for FP/FN
    match_type: str  # "TP", "FP", or "FN"
    label_id: UUID


def _iou(b1: tuple[int, int, int, int], b2: tuple[int, int, int, int]) -> float:
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    ix1, iy1 = max(x1, x2), max(y1, y2)
    ix2, iy2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0


def _match_single_image(
    sample_id: UUID,
    img_gt: list[ODAnnotation],
    img_pred: list[ODAnnotation],
    iou_threshold: float,
    confidence_threshold: float,
) -> list[MatchRecord]:
    """Match predictions to GTs for one image and return TP/FP/FN records."""
    records: list[MatchRecord] = []
    matched_gt: set[UUID] = set()

    for pred_ann in sorted(img_pred, key=lambda a: a.confidence, reverse=True):
        if pred_ann.confidence < confidence_threshold:
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_ann.annotation_id,
                    gt_id=None,
                    iou=None,
                    match_type="FP",
                    label_id=pred_ann.label_id,
                )
            )
            continue

        best_iou = iou_threshold - 1e-9
        best_gt: ODAnnotation | None = None
        for gt_ann in img_gt:
            if gt_ann.annotation_id in matched_gt or gt_ann.label_id != pred_ann.label_id:
                continue
            iou = _iou(
                (pred_ann.x, pred_ann.y, pred_ann.w, pred_ann.h),
                (gt_ann.x, gt_ann.y, gt_ann.w, gt_ann.h),
            )
            if iou > best_iou:
                best_iou, best_gt = iou, gt_ann

        if best_gt is not None:
            matched_gt.add(best_gt.annotation_id)
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_ann.annotation_id,
                    gt_id=best_gt.annotation_id,
                    iou=round(best_iou, 4),
                    match_type="TP",
                    label_id=pred_ann.label_id,
                )
            )
        else:
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_ann.annotation_id,
                    gt_id=None,
                    iou=None,
                    match_type="FP",
                    label_id=pred_ann.label_id,
                )
            )

    for gt_ann in img_gt:
        if gt_ann.annotation_id not in matched_gt:
            records.append(
                MatchRecord(
                    sample_id=sample_id,
                    pred_id=None,
                    gt_id=gt_ann.annotation_id,
                    iou=None,
                    match_type="FN",
                    label_id=gt_ann.label_id,
                )
            )
    return records


def match_annotations(
    gt: list[ODAnnotation],
    pred: list[ODAnnotation],
    iou_threshold: float,
    confidence_threshold: float,
) -> list[MatchRecord]:
    """Class-aware greedy matching across all images; returns TP/FP/FN records."""
    gt_by_image: dict[UUID, list[ODAnnotation]] = defaultdict(list)
    for ann in gt:
        gt_by_image[ann.sample_id].append(ann)

    pred_by_image: dict[UUID, list[ODAnnotation]] = defaultdict(list)
    for ann in pred:
        pred_by_image[ann.sample_id].append(ann)

    records: list[MatchRecord] = []
    for sample_id in set(gt_by_image.keys()) | set(pred_by_image.keys()):
        records.extend(
            _match_single_image(
                sample_id,
                gt_by_image[sample_id],
                pred_by_image[sample_id],
                iou_threshold,
                confidence_threshold,
            )
        )
    return records


def _compute_ap(tp_flags: list[bool], total_gt: int) -> float:
    """AP via 101-point interpolation over the precision-recall curve."""
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
    for t in np.linspace(0, 1, 101):
        prec_at_rec = [p for p, r in zip(precisions, recalls) if r >= t]
        ap += max(prec_at_rec) if prec_at_rec else 0.0
    return ap / 101


def compute_metrics(
    matches: list[MatchRecord],
    pred_confidences: dict[UUID, float],
    label_names: dict[UUID, str],
) -> dict:
    """Compute OD metrics from a (possibly tag-filtered) set of match records.

    Args:
        matches: Output of match_annotations(), optionally pre-filtered by tag.
        pred_confidences: Maps every prediction annotation_id to its confidence.
            Used to sort predictions for per-class AP computation.
        label_names: Maps label_id → human-readable class name.

    Returns:
        Dict: precision, recall, f1, mAP, per_class_metrics.
    """
    tp = sum(1 for m in matches if m.match_type == "TP")
    fp = sum(1 for m in matches if m.match_type == "FP")
    fn = sum(1 for m in matches if m.match_type == "FN")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Per-class AP: collect TP/FP flags per class sorted by confidence
    tp_lookup: dict[UUID, bool] = {
        m.pred_id: (m.match_type == "TP") for m in matches if m.pred_id is not None
    }
    pred_records_by_label: dict[UUID, list[tuple[float, bool]]] = defaultdict(list)
    for m in matches:
        if m.pred_id is not None:
            conf = pred_confidences.get(m.pred_id, 0.0)
            pred_records_by_label[m.label_id].append((conf, tp_lookup[m.pred_id]))

    gt_count_by_label: dict[UUID, int] = defaultdict(int)
    for m in matches:
        if m.match_type in ("TP", "FN"):
            gt_count_by_label[m.label_id] += 1

    all_label_ids = set(pred_records_by_label.keys()) | set(gt_count_by_label.keys())
    per_class: dict[str, dict] = {}
    ap_values: list[float] = []

    for label_id in all_label_ids:
        sorted_preds = sorted(pred_records_by_label[label_id], key=lambda x: x[0], reverse=True)
        tp_flags = [is_tp for _, is_tp in sorted_preds]
        total_gt = gt_count_by_label[label_id]

        ap = _compute_ap(tp_flags, total_gt)
        ap_values.append(ap)

        class_tp = sum(tp_flags)
        class_fp = len(tp_flags) - class_tp
        class_fn = total_gt - class_tp
        cls_prec = class_tp / (class_tp + class_fp) if (class_tp + class_fp) > 0 else 0.0
        cls_rec = class_tp / (class_tp + class_fn) if (class_tp + class_fn) > 0 else 0.0
        cls_f1 = 2 * cls_prec * cls_rec / (cls_prec + cls_rec) if (cls_prec + cls_rec) > 0 else 0.0

        name = label_names.get(label_id, str(label_id))
        per_class[name] = {
            "ap": round(ap, 4),
            "precision": round(cls_prec, 4),
            "recall": round(cls_rec, 4),
            "f1": round(cls_f1, 4),
        }

    m_ap = float(np.mean(ap_values)) if ap_values else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP": round(m_ap, 4),
        "per_class_metrics": per_class,
    }
