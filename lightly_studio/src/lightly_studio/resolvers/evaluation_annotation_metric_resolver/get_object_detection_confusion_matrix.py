"""Build a object-detection confusion matrix from persisted pairing metrics."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    ObjectDetectionConfusionMatrix,
)


def get_object_detection_confusion_matrix(
    session: Session,
    evaluation_run_id: UUID,
) -> ObjectDetectionConfusionMatrix:
    """Aggregate persisted OD pairing metrics into a label-by-label matrix.

    Counts are computed in a single SQL query that joins
    ``evaluation_annotation_metric`` to ``annotation_base`` and ``annotation_label``
    twice (once for ground truth, once for prediction) and groups by the resolved
    label name pair. Rows are then bucketed as follows:

    - Both ``pred_annotation_id`` and ``gt_annotation_id`` set: true positive at
      ``[gt_label][pred_label]``.
    - Only ``pred_annotation_id`` (``gt_label`` is ``NULL``): false positive at
      ``[NO_GROUND_TRUTH_ROW_LABEL][pred_label]``.
    - Only ``gt_annotation_id`` (``pred_label`` is ``NULL``): false negative at
      ``[gt_label][NO_PREDICTION_COL_LABEL]``.

    Args:
        session: Active database session.
        evaluation_run_id: Evaluation run whose pairing metrics should be aggregated.

    Returns:
        Matrix with sorted class labels and optional synthetic FP/FN row/column.
    """
    grouped_rows = _fetch_pair_counts(session=session, evaluation_run_id=evaluation_run_id)
    if not grouped_rows:
        return ObjectDetectionConfusionMatrix(
            row_labels=[],
            col_labels=[],
            counts=[],
        )

    row_labels, col_labels = _build_axis_labels(grouped_rows=grouped_rows)
    counts = _build_counts_grid(
        grouped_rows=grouped_rows,
        row_labels=row_labels,
        col_labels=col_labels,
    )
    return ObjectDetectionConfusionMatrix(
        row_labels=row_labels,
        col_labels=col_labels,
        counts=counts,
    )


def _fetch_pair_counts(
    session: Session,
    evaluation_run_id: UUID,
) -> list[tuple[str | None, str | None, int]]:
    """Return ``(gt_label, pred_label, count)`` triples grouped in SQL.

    LEFT JOINs the metric table to ``annotation_base`` and ``annotation_label`` for
    both gt and pred sides so that FP and FN rows surface as ``NULL`` on the missing
    side. Counting and grouping happen in the database, so the Python side only
    receives at most one row per ``(gt_label, pred_label)`` pair.

    Args:
        session: Active database session.
        evaluation_run_id: Evaluation run whose pairing metrics should be aggregated.

    Returns:
        Group rows. ``NULL`` ``gt_label`` denotes the FP bucket; ``NULL`` ``pred_label``
        denotes the FN bucket.
    """
    gt_annotation = aliased(AnnotationBaseTable)
    pred_annotation = aliased(AnnotationBaseTable)
    gt_label = aliased(AnnotationLabelTable)
    pred_label = aliased(AnnotationLabelTable)

    stmt = (
        select(
            gt_label.annotation_label_name,
            pred_label.annotation_label_name,
            func.count().label("n"),
        )
        .select_from(EvaluationAnnotationMetricTable)
        .join(
            gt_annotation,
            col(EvaluationAnnotationMetricTable.gt_annotation_id) == col(gt_annotation.sample_id),
            isouter=True,
        )
        .join(
            pred_annotation,
            col(EvaluationAnnotationMetricTable.pred_annotation_id)
            == col(pred_annotation.sample_id),
            isouter=True,
        )
        .join(
            gt_label,
            col(gt_annotation.annotation_label_id) == col(gt_label.annotation_label_id),
            isouter=True,
        )
        .join(
            pred_label,
            col(pred_annotation.annotation_label_id) == col(pred_label.annotation_label_id),
            isouter=True,
        )
        .where(col(EvaluationAnnotationMetricTable.evaluation_run_id) == evaluation_run_id)
        .group_by(gt_label.annotation_label_name, pred_label.annotation_label_name)
    )

    return [(row[0], row[1], row[2]) for row in session.exec(stmt).all()]


def _build_axis_labels(
    grouped_rows: list[tuple[str | None, str | None, int]],
) -> tuple[list[str], list[str]]:
    """Build sorted row and column label lists, appending synthetic FP/FN labels when needed.

    A ``NULL`` ``gt_label`` in any row means at least one FP exists and triggers the
    synthetic ground-truth row; symmetrically a ``NULL`` ``pred_label`` triggers the
    synthetic prediction column.

    Args:
        grouped_rows: SQL group rows from :func:`_fetch_pair_counts`.

    Returns:
        ``(row_labels, col_labels)`` ready for dense matrix construction.
    """
    row_labels = sorted({gt_name for gt_name, _, _ in grouped_rows if gt_name is not None})
    if any(gt_name is None for gt_name, _, _ in grouped_rows):
        row_labels.append(NO_GROUND_TRUTH_ROW_LABEL)

    col_labels = sorted({pred_name for _, pred_name, _ in grouped_rows if pred_name is not None})
    if any(pred_name is None for _, pred_name, _ in grouped_rows):
        col_labels.append(NO_PREDICTION_COL_LABEL)

    return row_labels, col_labels


def _build_counts_grid(
    grouped_rows: list[tuple[str | None, str | None, int]],
    row_labels: list[str],
    col_labels: list[str],
) -> list[list[int]]:
    """Scatter SQL group rows into a 2D integer grid aligned with the given axes.

    ``NULL`` label names from the SQL LEFT JOINs are mapped to the synthetic
    FP/FN bucket labels before lookup.

    Args:
        grouped_rows: SQL group rows from :func:`_fetch_pair_counts`.
        row_labels: Ground-truth axis order.
        col_labels: Prediction axis order.

    Returns:
        ``counts[i][j]`` aligned with ``row_labels[i]`` and ``col_labels[j]`` (zeros elsewhere).
    """
    row_index = {name: i for i, name in enumerate(row_labels)}
    col_index = {name: j for j, name in enumerate(col_labels)}
    counts = [[0 for _ in col_labels] for _ in row_labels]
    for gt_name, pred_name, n in grouped_rows:
        row_key = gt_name if gt_name is not None else NO_GROUND_TRUTH_ROW_LABEL
        col_key = pred_name if pred_name is not None else NO_PREDICTION_COL_LABEL
        counts[row_index[row_key]][col_index[col_key]] = n
    return counts
