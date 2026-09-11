"""Derive aggregate metrics from an evaluation confusion matrix."""

from __future__ import annotations

from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    ConfusionMatrix,
)
from lightly_studio.models.evaluation_metrics import ClassMetrics, EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationTaskType


def compute_from_confusion_matrix(
    matrix: ConfusionMatrix,
    task_type: EvaluationTaskType,
) -> EvaluationMetrics:
    """Derive per-class and micro-averaged metrics from a confusion matrix.

    Precision, recall, and F1 come from the class-by-class counts. Each class
    column includes the false-positive row and each class row includes the
    false-negative column, so unmatched predictions and ground truths are
    counted. Accuracy is the fraction of pairings on the diagonal; it is
    meaningful only for classification and is ``None`` for other task types.

    Args:
        matrix: Confusion matrix of the run.
        task_type: Task type of the run, used to decide whether accuracy applies.

    Returns:
        The aggregate metrics for the run.
    """
    class_labels = [label for label in matrix.row_labels if label != NO_GROUND_TRUTH_ROW_LABEL]
    row_index = {label: i for i, label in enumerate(matrix.row_labels)}
    col_index = {label: j for j, label in enumerate(matrix.col_labels)}

    per_class: list[ClassMetrics] = []
    total_true_positives = 0
    total_predicted = 0
    total_ground_truth = 0
    for label in class_labels:
        column = col_index[label]
        class_row = matrix.counts[row_index[label]]
        true_positives = class_row[column]
        predicted = sum(matrix_row[column] for matrix_row in matrix.counts)
        ground_truth = sum(class_row)
        precision = _ratio(true_positives, predicted)
        recall = _ratio(true_positives, ground_truth)
        per_class.append(
            ClassMetrics(
                label=label,
                precision=precision,
                recall=recall,
                f1=_f1(precision, recall),
                support=ground_truth,
            )
        )
        total_true_positives += true_positives
        total_predicted += predicted
        total_ground_truth += ground_truth

    micro_precision = _ratio(total_true_positives, total_predicted)
    micro_recall = _ratio(total_true_positives, total_ground_truth)
    total_pairings = sum(sum(row) for row in matrix.counts)
    return EvaluationMetrics(
        per_class=per_class,
        precision=micro_precision,
        recall=micro_recall,
        f1=_f1(micro_precision, micro_recall),
        accuracy=(
            _ratio(total_true_positives, total_pairings)
            if task_type == EvaluationTaskType.CLASSIFICATION
            else None
        ),
    )


def _ratio(numerator: int, denominator: int) -> float:
    """Return ``numerator / denominator``, or 0.0 when the denominator is 0."""
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    """Return the harmonic mean of precision and recall, or 0.0 when both are 0."""
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0
