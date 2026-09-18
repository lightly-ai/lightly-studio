"""Aggregate evaluation metrics derived from a confusion matrix."""

from __future__ import annotations

from pydantic import BaseModel


class ClassMetrics(BaseModel):
    """Per-class precision, recall, and F1 for one evaluation run.

    Attributes:
        label: Annotation label name.
        precision: True positives over predictions of this class. 0 when the class
            is never predicted.
        recall: True positives over ground truths of this class. 0 when the class
            has no ground truth.
        f1: Harmonic mean of precision and recall. 0 when both are 0.
        support: Number of ground-truth annotations of this class.
    """

    label: str
    precision: float
    recall: float
    f1: float
    support: int


class EvaluationMetrics(BaseModel):
    """Aggregate metrics for an evaluation run, derived from its confusion matrix.

    Attributes:
        per_class: Per-class precision, recall, F1, and support.
        precision: Micro-averaged precision over the pooled per-class counts.
        recall: Micro-averaged recall over the pooled per-class counts.
        f1: Harmonic mean of the micro-averaged precision and recall.
        accuracy: Fraction of correctly classified samples. Set for classification
            runs; ``None`` for object detection, where predictions and ground
            truths are matched rather than compared one to one.
    """

    per_class: list[ClassMetrics]
    precision: float
    recall: float
    f1: float
    accuracy: float | None


class ClassAveragePrecision(BaseModel):
    """Average precision of one class in an object-detection run.

    Attributes:
        label: Annotation label name.
        average_precision: Average precision, averaged over the IoU thresholds.
    """

    label: str
    average_precision: float


class DetectionAveragePrecision(BaseModel):
    """Mean average precision of an object-detection run.

    Attributes:
        mean_average_precision: Mean of the per-class average precision.
        per_class: Per-class average precision, for every class in the ground truth.
        iou_thresholds: IoU thresholds the average precision is averaged over.
    """

    mean_average_precision: float
    per_class: list[ClassAveragePrecision]
    iou_thresholds: list[float]
