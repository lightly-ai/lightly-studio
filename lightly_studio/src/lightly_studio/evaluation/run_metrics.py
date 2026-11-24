"""Aggregate metrics of a persisted evaluation run, for all its images or a tag."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation import aggregate_metrics, average_precision, object_detection_metric
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_class_metric_resolver,
    evaluation_sample_metric_resolver,
)


def compute_run_metrics(session: Session, evaluation_run: EvaluationRunTable) -> EvaluationMetrics:
    """Return the aggregate metrics of an evaluation run.

    Derives per-class and micro-averaged precision, recall, and F1 from the run's
    confusion matrix, plus accuracy for classification runs. For object-detection runs
    created with ``compute_average_precision=True`` it also includes the per-class and
    mean average precision.

    Args:
        session: Database session.
        evaluation_run: The run. The caller checks that it belongs to the expected dataset.

    Returns:
        The aggregate metrics for the run.

    Raises:
        NotImplementedError: If the run's task type has no confusion matrix.
    """
    metrics = _confusion_metrics(session=session, evaluation_run=evaluation_run, tag_id=None)
    if evaluation_run.task_type != EvaluationTaskType.OBJECT_DETECTION:
        return metrics
    by_label = average_precision.by_label_and_threshold(
        class_metrics=evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
            session=session, evaluation_run_id=evaluation_run.id
        ),
        run_config=evaluation_run.config_json,
    )
    return _with_named_average_precision(session=session, metrics=metrics, by_label=by_label)


def compute_slice_metrics(
    session: Session, evaluation_run: EvaluationRunTable, tag_id: UUID
) -> EvaluationMetrics:
    """Return the aggregate metrics of a run on its evaluated images with a tag.

    Precision, recall, F1, and accuracy come from the stored pairings of the tagged
    images. The average precision is not stored for a subset, so it is computed again
    from the annotations of the tagged images, for object-detection runs created with
    ``compute_average_precision=True``.

    Args:
        session: Database session.
        evaluation_run: The run. The caller checks that it belongs to the expected dataset.
        tag_id: The tag that selects the images.

    Returns:
        The aggregate metrics of the run on the tagged images.

    Raises:
        NotImplementedError: If the run's task type has no confusion matrix.
    """
    metrics = _confusion_metrics(session=session, evaluation_run=evaluation_run, tag_id=tag_id)
    if not _has_average_precision(evaluation_run=evaluation_run):
        return metrics
    sample_ids = evaluation_sample_metric_resolver.get_sample_ids_by_evaluation_run_id(
        session=session, evaluation_run_id=evaluation_run.id, tag_id=tag_id
    )
    gt_per_sample = _load_boxes(
        session=session,
        sample_ids=sample_ids,
        annotation_collection_id=evaluation_run.gt_annotation_collection_id,
    )
    pred_per_sample = _load_boxes(
        session=session,
        sample_ids=sample_ids,
        annotation_collection_id=evaluation_run.pred_annotation_collection_id,
    )
    entries = average_precision.compute(
        gt_per_image=[gt_per_sample.get(sample_id, []) for sample_id in sample_ids],
        pred_per_image=[pred_per_sample.get(sample_id, []) for sample_id in sample_ids],
        iou_thresholds=average_precision.COCO_IOU_THRESHOLDS,
    )
    by_label: dict[UUID, dict[float, float]] = {}
    for entry in entries:
        by_label.setdefault(entry.label_id, {})[entry.iou_threshold] = entry.average_precision
    return _with_named_average_precision(session=session, metrics=metrics, by_label=by_label)


def _confusion_metrics(
    session: Session, evaluation_run: EvaluationRunTable, tag_id: UUID | None
) -> EvaluationMetrics:
    if not evaluation_annotation_metric_resolver.supports_confusion_matrix(
        evaluation_run.task_type
    ):
        raise NotImplementedError(
            f"Evaluation task type {evaluation_run.task_type.value!r} has no confusion matrix."
        )
    matrix = evaluation_annotation_metric_resolver.get_confusion_matrix(
        session=session, evaluation_run_id=evaluation_run.id, tag_id=tag_id
    )
    return aggregate_metrics.compute_aggregate_metrics_from_confusion_matrix(
        matrix=matrix, task_type=evaluation_run.task_type
    )


def _has_average_precision(evaluation_run: EvaluationRunTable) -> bool:
    return (
        evaluation_run.task_type == EvaluationTaskType.OBJECT_DETECTION
        and evaluation_run.config_json.get("compute_average_precision") is True
    )


def _load_boxes(
    session: Session, sample_ids: Sequence[UUID], annotation_collection_id: UUID
) -> dict[UUID, list[object_detection_metric.BoundingBox]]:
    annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=session,
        parent_sample_ids=sample_ids,
        annotation_collection_id=annotation_collection_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotations_per_sample: dict[UUID, list[AnnotationBaseTable]] = {}
    for annotation in annotations:
        annotations_per_sample.setdefault(annotation.parent_sample_id, []).append(annotation)
    return {
        sample_id: object_detection_metric.to_bounding_boxes(annotations=sample_annotations)
        for sample_id, sample_annotations in annotations_per_sample.items()
    }


def _with_named_average_precision(
    session: Session, metrics: EvaluationMetrics, by_label: dict[UUID, dict[float, float]]
) -> EvaluationMetrics:
    # Resolve names at read time, so renamed labels keep their values and deleted
    # labels are skipped.
    labels = annotation_label_resolver.get_by_ids(session=session, ids=list(by_label))
    return average_precision.with_average_precision(
        metrics=metrics,
        by_class={
            label.annotation_label_name: by_label[label.annotation_label_id] for label in labels
        },
    )
