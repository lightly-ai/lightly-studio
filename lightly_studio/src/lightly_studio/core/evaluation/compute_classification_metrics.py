"""Classification metrics for single-label image-level evaluation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID


@dataclass
class ClassificationAnnotation:
    """Flattened classification annotation used by the metrics engine."""

    annotation_id: UUID
    sample_id: UUID
    label_id: UUID
    confidence: float


@dataclass
class ClassificationMatchRecord:
    """One row in the per-annotation match table."""

    sample_id: UUID
    pred_id: UUID | None
    gt_id: UUID | None
    iou: float | None
    match_type: str
    label_id: UUID


def match_annotations(
    gt: list[ClassificationAnnotation],
    pred: list[ClassificationAnnotation],
) -> tuple[list[ClassificationMatchRecord], int]:
    """Match single-label classification annotations per sample.

    If multiple annotations exist per sample, the annotation with the highest
    confidence is used as the effective label for evaluation.

    Returns:
        Tuple of match records and total number of GT-labeled samples.
    """
    gt_by_sample = _select_top_annotation_per_sample(gt)
    pred_by_sample = _select_top_annotation_per_sample(pred)

    records: list[ClassificationMatchRecord] = []
    for sample_id in gt_by_sample.keys() | pred_by_sample.keys():
        gt_ann = gt_by_sample.get(sample_id)
        pred_ann = pred_by_sample.get(sample_id)

        if gt_ann is not None and pred_ann is not None and gt_ann.label_id == pred_ann.label_id:
            records.append(
                ClassificationMatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_ann.annotation_id,
                    gt_id=gt_ann.annotation_id,
                    iou=None,
                    match_type="TP",
                    label_id=gt_ann.label_id,
                )
            )
            continue

        if pred_ann is not None:
            records.append(
                ClassificationMatchRecord(
                    sample_id=sample_id,
                    pred_id=pred_ann.annotation_id,
                    gt_id=None,
                    iou=None,
                    match_type="FP",
                    label_id=pred_ann.label_id,
                )
            )
        if gt_ann is not None:
            records.append(
                ClassificationMatchRecord(
                    sample_id=sample_id,
                    pred_id=None,
                    gt_id=gt_ann.annotation_id,
                    iou=None,
                    match_type="FN",
                    label_id=gt_ann.label_id,
                )
            )

    return (records, len(gt_by_sample))


def compute_metrics(
    matches: list[ClassificationMatchRecord],
    total_gt_samples: int,
    label_names: dict[UUID, str],
) -> dict:
    """Compute single-label classification metrics from match records."""
    tp_by_label: dict[UUID, int] = defaultdict(int)
    fp_by_label: dict[UUID, int] = defaultdict(int)
    fn_by_label: dict[UUID, int] = defaultdict(int)

    for match in matches:
        if match.match_type == "TP":
            tp_by_label[match.label_id] += 1
        elif match.match_type == "FP":
            fp_by_label[match.label_id] += 1
        elif match.match_type == "FN":
            fn_by_label[match.label_id] += 1

    label_ids = set(tp_by_label) | set(fp_by_label) | set(fn_by_label)
    per_class_metrics: dict[str, dict[str, float | int]] = {}

    precision_values: list[float] = []
    recall_values: list[float] = []
    f1_values: list[float] = []

    for label_id in label_ids:
        tp = tp_by_label[label_id]
        fp = fp_by_label[label_id]
        fn = fn_by_label[label_id]
        support = tp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        precision_values.append(precision)
        recall_values.append(recall)
        f1_values.append(f1)

        per_class_metrics[label_names.get(label_id, str(label_id))] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    accuracy = sum(tp_by_label.values()) / total_gt_samples if total_gt_samples > 0 else 0.0
    macro_precision = sum(precision_values) / len(precision_values) if precision_values else 0.0
    macro_recall = sum(recall_values) / len(recall_values) if recall_values else 0.0
    macro_f1 = sum(f1_values) / len(f1_values) if f1_values else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(macro_precision, 4),
        "recall": round(macro_recall, 4),
        "f1": round(macro_f1, 4),
        "per_class_metrics": per_class_metrics,
    }


def _select_top_annotation_per_sample(
    annotations: list[ClassificationAnnotation],
) -> dict[UUID, ClassificationAnnotation]:
    selected: dict[UUID, ClassificationAnnotation] = {}
    for annotation in annotations:
        current = selected.get(annotation.sample_id)
        if current is None or annotation.confidence > current.confidence:
            selected[annotation.sample_id] = annotation
    return selected
