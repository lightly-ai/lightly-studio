"""Tests for the recompute_evaluation_run service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session

from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from lightly_studio.services import evaluation_service
from tests.api.routes.api.evaluation import helpers


def test_recompute_evaluation_run__clears_staleness_and_preserves_run(
    db_session: Session,
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(iou_threshold=0.5, classwise=True),
        name="run-1",
    )
    run_id = result.evaluation_run_id
    initial_run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert initial_run is not None
    original_created_at = initial_run.created_at

    run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run is not None
    run.stale_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    recomputed = evaluation_service.recompute_evaluation_run(session=db_session, run=run)

    assert recomputed.evaluation_run_id == run_id
    assert recomputed.sample_count == result.sample_count
    assert recomputed.gt_annotation_count == result.gt_annotation_count
    assert recomputed.pred_annotation_count == result.pred_annotation_count

    run_after = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run_after is not None
    assert run_after.stale_since is None
    assert run_after.created_at == original_created_at
    assert run_after.id == run_id


def test_recompute_evaluation_run__produces_fresh_metrics(db_session: Session) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        name="run-1",
    )
    run_id = result.evaluation_run_id

    old_sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_id
    )
    old_annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_id
    )
    assert len(old_sample_metrics) > 0
    assert len(old_annotation_metrics) > 0

    run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run is not None
    evaluation_service.recompute_evaluation_run(session=db_session, run=run)

    new_sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_id
    )
    new_annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_id
    )
    assert len(new_sample_metrics) == len(old_sample_metrics)
    assert len(new_annotation_metrics) == len(old_annotation_metrics)


def test_recompute_evaluation_run__idempotent_on_non_stale_run(db_session: Session) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        name="run-1",
    )
    run_id = result.evaluation_run_id

    run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run is not None
    assert run.stale_since is None

    recomputed = evaluation_service.recompute_evaluation_run(session=db_session, run=run)

    assert recomputed.evaluation_run_id == run_id
    assert recomputed.sample_count == result.sample_count
    run_after = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run_after is not None
    assert run_after.stale_since is None


def test_recompute_evaluation_run__classification(db_session: Session) -> None:
    root = helpers.create_dataset_with_annotations(
        db_session, annotation_type=AnnotationType.CLASSIFICATION
    )

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.CLASSIFICATION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ClassificationEvaluationConfig(),
        name="run-1",
    )
    run_id = result.evaluation_run_id

    run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run is not None
    recomputed = evaluation_service.recompute_evaluation_run(session=db_session, run=run)

    assert recomputed.evaluation_run_id == run_id
    assert recomputed.sample_count == result.sample_count
    run_after = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id)
    assert run_after is not None
    assert run_after.stale_since is None
