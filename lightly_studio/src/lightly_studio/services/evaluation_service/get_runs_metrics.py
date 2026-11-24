"""Aggregate metrics of several evaluation runs, for comparison."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.errors import NotFoundError, UnsupportedEvaluationTaskTypeError
from lightly_studio.evaluation import run_metrics
from lightly_studio.models.evaluation_metrics import (
    EvaluationRunMetricsView,
    EvaluationSliceMetricsView,
)
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
    tag_resolver,
)


def get_runs_metrics(
    session: Session,
    dataset_id: UUID,
    evaluation_run_ids: Sequence[UUID],
    tag_ids: Sequence[UUID] = (),
) -> list[EvaluationRunMetricsView]:
    """Return the aggregate metrics and the evaluated sample set of each run.

    Args:
        session: Database session.
        dataset_id: The dataset that all runs must belong to.
        evaluation_run_ids: The runs, in the order of the result.
        tag_ids: Tags to compute the metrics of each run on, in the order of the slices.

    Returns:
        One view for each run, in the order of ``evaluation_run_ids``.

    Raises:
        NotFoundError: If a run does not exist in the dataset, or a tag does not exist.
        UnsupportedEvaluationTaskTypeError: If a run has a task type without metrics.
    """
    runs = [
        _get_run_with_metrics(session=session, dataset_id=dataset_id, evaluation_run_id=run_id)
        for run_id in evaluation_run_ids
    ]
    tags = [_get_tag(session=session, dataset_id=dataset_id, tag_id=tag_id) for tag_id in tag_ids]
    return [_to_view(session=session, evaluation_run=run, tags=tags) for run in runs]


def _get_run_with_metrics(
    session: Session, dataset_id: UUID, evaluation_run_id: UUID
) -> EvaluationRunTable:
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=evaluation_run_id)
    if run is None or run.dataset_id != dataset_id:
        raise NotFoundError(f"Evaluation run {evaluation_run_id} not found in this dataset.")
    if not evaluation_annotation_metric_resolver.supports_confusion_matrix(run.task_type):
        raise UnsupportedEvaluationTaskTypeError(
            f"Evaluation task type {run.task_type.value!r} has no aggregate metrics."
        )
    return run


def _get_tag(session: Session, dataset_id: UUID, tag_id: UUID) -> TagTable:
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    collection = (
        None
        if tag is None
        else collection_resolver.get_by_id(session=session, collection_id=tag.collection_id)
    )
    if tag is None or collection is None or collection.dataset_id != dataset_id:
        raise NotFoundError(f"Tag {tag_id} not found in this dataset.")
    return tag


def _to_view(
    session: Session, evaluation_run: EvaluationRunTable, tags: Sequence[TagTable]
) -> EvaluationRunMetricsView:
    sample_set = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=session, evaluation_run_id=evaluation_run.id
    )
    return EvaluationRunMetricsView(
        evaluation_run_id=evaluation_run.id,
        metrics=run_metrics.compute_run_metrics(session=session, evaluation_run=evaluation_run),
        evaluated_sample_count=sample_set.sample_count,
        evaluated_sample_set_hash=sample_set.sample_set_hash,
        slices=[
            _to_slice_view(session=session, evaluation_run=evaluation_run, tag=tag) for tag in tags
        ],
    )


def _to_slice_view(
    session: Session, evaluation_run: EvaluationRunTable, tag: TagTable
) -> EvaluationSliceMetricsView:
    sample_set = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=session, evaluation_run_id=evaluation_run.id, tag_id=tag.tag_id
    )
    return EvaluationSliceMetricsView(
        tag_id=tag.tag_id,
        tag_name=tag.name,
        metrics=run_metrics.compute_slice_metrics(
            session=session, evaluation_run=evaluation_run, tag_id=tag.tag_id
        ),
        evaluated_sample_count=sample_set.sample_count,
    )
