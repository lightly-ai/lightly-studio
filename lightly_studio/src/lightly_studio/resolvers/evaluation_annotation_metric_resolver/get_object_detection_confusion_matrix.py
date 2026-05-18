"""Build a dense object-detection confusion matrix from persisted pairing metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    ObjectDetectionConfusionMatrix,
)
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver
from lightly_studio.resolvers.evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id import (  # noqa: E501
    get_all_by_evaluation_run_id,
)


@dataclass
class _PairAggregation:
    """Intermediate counts and axis metadata before materializing a dense matrix.

    Attributes:
        cell_counts: Map from ``(gt_label, pred_label)`` to occurrence count.
        gt_class_names: Real ground-truth class names seen in metrics (excludes synthetic row).
        pred_class_names: Real prediction class names seen in metrics (excludes synthetic col).
        has_fp: Whether any false-positive rows exist (pred-only metrics).
        has_fn: Whether any false-negative rows exist (gt-only metrics).
    """

    cell_counts: dict[tuple[str, str], int]
    gt_class_names: set[str]
    pred_class_names: set[str]
    has_fp: bool
    has_fn: bool


def get_object_detection_confusion_matrix(
    session: Session,
    evaluation_run_id: UUID,
) -> ObjectDetectionConfusionMatrix:
    """Aggregate persisted OD pairing metrics into a label-by-label matrix.

    Loads all ``evaluation_annotation_metric`` rows for ``evaluation_run_id``, resolves
    annotation and label names, then fills matrix cells as follows:

    - Both ``pred_annotation_id`` and ``gt_annotation_id`` set: true positive at
      ``[gt_label][pred_label]``.
    - Only ``pred_annotation_id``: false positive at
      ``[NO_GROUND_TRUTH_ROW_LABEL][pred_label]``.
    - Only ``gt_annotation_id``: false negative at
      ``[gt_label][NO_PREDICTION_COL_LABEL]``.

    Args:
        session: Active database session.
        evaluation_run_id: Evaluation run whose pairing metrics should be aggregated.

    Returns:
        Matrix with sorted class labels and optional synthetic FP/FN row/column.
    """
    metrics = get_all_by_evaluation_run_id(session=session, evaluation_run_id=evaluation_run_id)
    if not metrics:
        return ObjectDetectionConfusionMatrix(
            row_labels=[],
            col_labels=[],
            counts=[],
        )

    annotations_by_id, label_name_by_id = _resolve_annotation_labels(
        session=session,
        metrics=metrics,
    )
    agg = _aggregate_pair_counts(
        metrics=metrics,
        annotations_by_id=annotations_by_id,
        label_name_by_id=label_name_by_id,
    )
    row_labels, col_labels = _build_axis_labels(agg)
    counts = _materialize_counts(agg.cell_counts, row_labels=row_labels, col_labels=col_labels)
    return ObjectDetectionConfusionMatrix(
        row_labels=row_labels,
        col_labels=col_labels,
        counts=counts,
    )


def _resolve_annotation_labels(
    session: Session,
    metrics: list[EvaluationAnnotationMetricTable],
) -> tuple[dict[UUID, AnnotationBaseTable], dict[str, str]]:
    """Batch-load annotations and label names referenced by metric rows.

    Args:
        session: Active database session.
        metrics: Annotation metric rows for one evaluation run.

    Returns:
        Tuple of (annotation_id -> annotation row, label_id str -> label name).
    """
    annotation_ids: list[UUID] = []
    for row in metrics:
        if row.pred_annotation_id is not None:
            annotation_ids.append(row.pred_annotation_id)
        if row.gt_annotation_id is not None:
            annotation_ids.append(row.gt_annotation_id)

    annotations_by_id: dict[UUID, AnnotationBaseTable] = {}
    if annotation_ids:
        for ann in annotation_resolver.get_by_ids(
            session=session,
            annotation_ids=annotation_ids,
        ):
            annotations_by_id[ann.sample_id] = ann

    label_ids = [ann.annotation_label_id for ann in annotations_by_id.values()]
    label_name_by_id: dict[str, str] = {}
    if label_ids:
        label_name_by_id = annotation_label_resolver.names_by_ids(
            session=session,
            ids=label_ids,
        )
    return annotations_by_id, label_name_by_id


def _label_for_annotation(
    annotation_id: UUID,
    annotations_by_id: dict[UUID, AnnotationBaseTable],
    label_name_by_id: dict[str, str],
) -> str:
    """Resolve a single annotation id to its display label name.

    Args:
        annotation_id: Child annotation row id (``annotation_base.sample_id``).
        annotations_by_id: Preloaded annotations keyed by id.
        label_name_by_id: Map from ``str(annotation_label_id)`` to label name.

    Returns:
        Label name resolved from the preloaded maps.

    Raises:
        RuntimeError: If the annotation or its label cannot be resolved. Metric
            rows reference annotations via FK, so a miss here indicates data
            corruption that must not be silently bucketed into the matrix.
    """
    ann = annotations_by_id.get(annotation_id)
    if ann is None:
        raise RuntimeError(
            f"Annotation {annotation_id} referenced by evaluation metric was not found; "
            "metric row points at a non-existent annotation."
        )
    label_name = label_name_by_id.get(str(ann.annotation_label_id))
    if label_name is None:
        raise RuntimeError(
            f"Annotation label {ann.annotation_label_id} for annotation {annotation_id} "
            "was not found; annotation references a non-existent label."
        )
    return label_name


def _aggregate_pair_counts(
    metrics: list[EvaluationAnnotationMetricTable],
    annotations_by_id: dict[UUID, AnnotationBaseTable],
    label_name_by_id: dict[str, str],
) -> _PairAggregation:
    """Count pairing outcomes by ``(gt_label, pred_label)`` including synthetic axes.

    Args:
        metrics: Annotation metric rows for one evaluation run.
        annotations_by_id: Preloaded annotations keyed by id.
        label_name_by_id: Map from label id string to label name.

    Returns:
        Sparse cell counts plus flags and class name sets for axis construction.
    """
    cell_counts: dict[tuple[str, str], int] = defaultdict(int)
    gt_class_names: set[str] = set()
    pred_class_names: set[str] = set()
    has_fp = False
    has_fn = False

    for row in metrics:
        pred_id = row.pred_annotation_id
        gt_id = row.gt_annotation_id
        if pred_id is not None and gt_id is not None:
            gt_label = _label_for_annotation(
                gt_id,
                annotations_by_id=annotations_by_id,
                label_name_by_id=label_name_by_id,
            )
            pred_label = _label_for_annotation(
                pred_id,
                annotations_by_id=annotations_by_id,
                label_name_by_id=label_name_by_id,
            )
            gt_class_names.add(gt_label)
            pred_class_names.add(pred_label)
            cell_counts[(gt_label, pred_label)] += 1
        elif pred_id is not None:
            has_fp = True
            pred_label = _label_for_annotation(
                pred_id,
                annotations_by_id=annotations_by_id,
                label_name_by_id=label_name_by_id,
            )
            pred_class_names.add(pred_label)
            cell_counts[(NO_GROUND_TRUTH_ROW_LABEL, pred_label)] += 1
        elif gt_id is not None:
            has_fn = True
            gt_label = _label_for_annotation(
                gt_id,
                annotations_by_id=annotations_by_id,
                label_name_by_id=label_name_by_id,
            )
            gt_class_names.add(gt_label)
            cell_counts[(gt_label, NO_PREDICTION_COL_LABEL)] += 1

    return _PairAggregation(
        cell_counts=dict(cell_counts),
        gt_class_names=gt_class_names,
        pred_class_names=pred_class_names,
        has_fp=has_fp,
        has_fn=has_fn,
    )


def _build_axis_labels(agg: _PairAggregation) -> tuple[list[str], list[str]]:
    """Build sorted row and column label lists, appending synthetic FP/FN labels when needed.

    Args:
        agg: Sparse aggregation from :func:`_aggregate_pair_counts`.

    Returns:
        ``(row_labels, col_labels)`` ready for dense matrix materialization.
    """
    row_labels = sorted(agg.gt_class_names)
    if agg.has_fp:
        row_labels.append(NO_GROUND_TRUTH_ROW_LABEL)

    col_labels = sorted(agg.pred_class_names)
    if agg.has_fn:
        col_labels.append(NO_PREDICTION_COL_LABEL)
    return row_labels, col_labels


def _materialize_counts(
    cell_counts: dict[tuple[str, str], int],
    row_labels: list[str],
    col_labels: list[str],
) -> list[list[int]]:
    """Scatter sparse ``(gt_label, pred_label)`` counts into a dense 2D integer grid.

    Args:
        cell_counts: Non-zero cells keyed by label pair.
        row_labels: Ground-truth axis order.
        col_labels: Prediction axis order.

    Returns:
        ``counts[i][j]`` aligned with ``row_labels[i]`` and ``col_labels[j]`` (zeros elsewhere).
    """
    row_index = {name: i for i, name in enumerate(row_labels)}
    col_index = {name: j for j, name in enumerate(col_labels)}
    n_rows = len(row_labels)
    n_cols = len(col_labels)
    counts = [[0 for _ in range(n_cols)] for _ in range(n_rows)]
    for (gt_label, pred_label), n in cell_counts.items():
        i = row_index.get(gt_label)
        j = col_index.get(pred_label)
        if i is None or j is None:
            continue
        counts[i][j] = n
    return counts
