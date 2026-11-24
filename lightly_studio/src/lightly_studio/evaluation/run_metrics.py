"""Aggregate metrics of a persisted evaluation run."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.evaluation import aggregate_metrics, average_precision
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_class_metric_resolver,
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
    if not evaluation_annotation_metric_resolver.supports_confusion_matrix(
        evaluation_run.task_type
    ):
        raise NotImplementedError(
            f"Evaluation task type {evaluation_run.task_type.value!r} has no confusion matrix."
        )
    matrix = evaluation_annotation_metric_resolver.get_confusion_matrix(
        session=session, evaluation_run_id=evaluation_run.id
    )
    metrics = aggregate_metrics.compute_aggregate_metrics_from_confusion_matrix(
        matrix=matrix, task_type=evaluation_run.task_type
    )
    if evaluation_run.task_type != EvaluationTaskType.OBJECT_DETECTION:
        return metrics
    by_label = average_precision.by_label_and_threshold(
        class_metrics=evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
            session=session, evaluation_run_id=evaluation_run.id
        ),
        run_config=evaluation_run.config_json,
    )
    # Resolve names at read time, so renamed labels keep their values and deleted
    # labels are skipped.
    labels = annotation_label_resolver.get_by_ids(session=session, ids=list(by_label))
    return average_precision.with_average_precision(
        metrics=metrics,
        by_class={
            label.annotation_label_name: by_label[label.annotation_label_id] for label in labels
        },
    )
