"""Recompute an existing evaluation run in-place."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation import (
    classification_metric,
    object_detection_metric,
    semantic_segmentation_metric,
    validators,
)
from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)


def recompute_evaluation_run(
    session: Session,
    *,
    run: EvaluationRunTable,
) -> EvaluationResult:
    """Re-run an evaluation in-place, replacing its metrics.

    Deletes the run's existing ``EvaluationAnnotationMetric`` and
    ``EvaluationSampleMetric`` rows, re-runs evaluation using the run's stored
    ``task_type``, ``config_json``, ``gt_annotation_collection_id``, and
    ``pred_annotation_collection_id``, persists fresh metrics, and resets
    ``stale_since`` to ``None``. The run ID and ``created_at`` are preserved.

    Args:
        session: Database session.
        run: The evaluation run to recompute.

    Returns:
        Summary of the recomputed run, including its ID and input counts.
    """
    observed_stale_since = run.stale_since
    data = _fetch_annotations_for_run(session=session, run=run)
    evaluation_annotation_metric_resolver.delete_by_evaluation_run_id(
        session=session, evaluation_run_id=run.id
    )
    evaluation_sample_metric_resolver.delete_by_evaluation_run_id(
        session=session, evaluation_run_id=run.id
    )
    _persist_metrics(session=session, run=run, data=data)
    evaluation_run_resolver.clear_stale_since(
        session=session,
        evaluation_run_id=run.id,
        expected_stale_since=observed_stale_since,
    )
    return EvaluationResult.from_evaluation_data(data)


def _fetch_annotations_for_run(session: Session, run: EvaluationRunTable) -> EvaluationData:
    """Fetch coverage and annotations from the run's stored collection IDs."""
    annotation_type = validators.get_annotation_type_for_task(run.task_type)
    gt_covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=session,
            annotation_collection_id=run.gt_annotation_collection_id,
        )
    )
    pred_covered = set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=session,
            annotation_collection_id=run.pred_annotation_collection_id,
        )
    )
    selected_sample_ids = gt_covered & pred_covered
    gt_annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=session,
        parent_sample_ids=list(selected_sample_ids),
        annotation_collection_id=run.gt_annotation_collection_id,
        annotation_type=annotation_type,
    )
    pred_annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=session,
        parent_sample_ids=list(selected_sample_ids),
        annotation_collection_id=run.pred_annotation_collection_id,
        annotation_type=annotation_type,
    )
    return EvaluationData(
        evaluation_run_id=run.id,
        selected_sample_ids=selected_sample_ids,
        gt_per_sample=_group_by_parent_sample_id(gt_annotations),
        pred_per_sample=_group_by_parent_sample_id(pred_annotations),
    )


def _persist_metrics(session: Session, run: EvaluationRunTable, data: EvaluationData) -> None:
    """Compute and persist fresh metrics for the run's task type."""
    if run.task_type == EvaluationTaskType.OBJECT_DETECTION:
        config = ObjectDetectionEvaluationConfig.model_validate(run.config_json)
        object_detection_metric.create_and_persist_object_detection_metrics_per_sample(
            session=session,
            data=data,
            iou_threshold=config.iou_threshold,
            classwise=config.classwise,
        )
    elif run.task_type == EvaluationTaskType.CLASSIFICATION:
        ClassificationEvaluationConfig.model_validate(run.config_json)
        classification_metric.create_and_persist_classification_metrics_per_sample(
            session=session,
            data=data,
        )
    elif run.task_type == EvaluationTaskType.SEMANTIC_SEGMENTATION:
        SemanticSegmentationEvaluationConfig.model_validate(run.config_json)
        semantic_segmentation_metric.create_and_persist_semantic_segmentation_metrics_per_sample(
            session=session,
            data=data,
        )
    else:
        raise ValueError(f"Unsupported evaluation task type: {run.task_type!r}")


def _group_by_parent_sample_id(
    annotations: list[AnnotationBaseTable],
) -> dict[UUID, list[AnnotationBaseTable]]:
    """Group annotation rows by their parent image sample id."""
    grouped: dict[UUID, list[AnnotationBaseTable]] = {}
    for annotation in annotations:
        grouped.setdefault(annotation.parent_sample_id, []).append(annotation)
    return grouped
