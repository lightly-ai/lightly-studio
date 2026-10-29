"""Aggregate evaluation metrics of an evaluation run."""

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
        average_precision: COCO average precision, averaged over the IoU thresholds
            0.50 to 0.95. Set for object-detection runs with
            ``compute_average_precision=True`` and a class with ground truth;
            ``None`` otherwise.
        average_precision_by_iou_threshold: Average precision at each IoU threshold,
            for example ``{0.5: ..., 0.55: ..., ..., 0.95: ...}``. Set like
            ``average_precision``.
    """

    label: str
    precision: float
    recall: float
    f1: float
    support: int
    average_precision: float | None = None
    average_precision_by_iou_threshold: dict[float, float] | None = None


class EvaluationMetrics(BaseModel):
    """Aggregate metrics for an evaluation run.

    Precision, recall, F1, and accuracy are derived from the confusion matrix. The
    average precision fields are derived from the stored per-class values.

    Attributes:
        per_class: Per-class precision, recall, F1, and support.
        precision: Micro-averaged precision over the pooled per-class counts.
        recall: Micro-averaged recall over the pooled per-class counts.
        f1: Harmonic mean of the micro-averaged precision and recall.
        accuracy: Fraction of correctly classified samples. Set for classification
            runs; ``None`` for object detection, where predictions and ground
            truths are matched rather than compared one to one.
        mean_average_precision: Mean of the per-class ``average_precision`` over the
            classes with ground truth. Set for object-detection runs with
            ``compute_average_precision=True``; ``None`` otherwise.
        mean_average_precision_by_iou_threshold: Mean over the classes of the average
            precision at each IoU threshold. Set like ``mean_average_precision``.
    """

    per_class: list[ClassMetrics]
    precision: float
    recall: float
    f1: float
    accuracy: float | None
    mean_average_precision: float | None = None
    mean_average_precision_by_iou_threshold: dict[float, float] | None = None
