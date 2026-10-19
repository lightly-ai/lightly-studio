"""Tests for the recompute_evaluation_run service."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.database.db_manager import DatabaseEngine
from lightly_studio.evaluation import object_detection_metric
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    InstanceSegmentationEvaluationConfig,
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


def test_recompute_evaluation_run__instance_segmentation(db_session: Session) -> None:
    # The GT and prediction masks cover the whole 1920x1080 image, so they match as one TP.
    root = helpers.create_dataset_with_annotations(
        db_session,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "segmentation_mask": [0, 1920 * 1080],
        },
    )

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.INSTANCE_SEGMENTATION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=InstanceSegmentationEvaluationConfig(),
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
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_id
    )
    assert {metric.metric_name: metric.value for metric in sample_metrics} == {
        "tp": 1.0,
        "fp": 0.0,
        "fn": 0.0,
    }


@pytest.mark.parametrize("rollback_fails", [False, True])
@pytest.mark.parametrize("after_persist", [False, True])
def test_recompute_evaluation_run__failure_restores_results(
    db_session: Session,
    mocker: MockerFixture,
    rollback_fails: bool,
    after_persist: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        name="original",
    )
    run = evaluation_run_resolver.get_by_id(
        session=db_session, evaluation_id=result.evaluation_run_id
    )
    assert run is not None
    run.stale_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    before = run.model_dump()
    resolvers = (evaluation_sample_metric_resolver, evaluation_annotation_metric_resolver)
    old_metrics = [
        [
            row.model_dump()
            for row in resolver.get_all_by_evaluation_run_id(
                session=db_session, evaluation_run_id=run.id
            )
        ]
        for resolver in resolvers
    ]
    persist = object_detection_metric.create_and_persist_object_detection_metrics_per_sample

    def fail(*args: Any, **kwargs: Any) -> None:
        if after_persist:
            persist(*args, **kwargs)
        raise ValueError("Evaluation failed")

    mocker.patch.object(
        object_detection_metric,
        "create_and_persist_object_detection_metrics_per_sample",
        side_effect=fail,
    )
    if rollback_fails:
        rollback = db_session.rollback

        def fail_rollback() -> None:
            rollback()
            raise RuntimeError("Rollback failed")

        mocker.patch.object(db_session, "rollback", side_effect=fail_rollback)
    with pytest.raises(ValueError, match="Evaluation failed"):
        evaluation_service.recompute_evaluation_run(session=db_session, run=run)
    if rollback_fails:
        assert "Rollback failed after evaluation rerun error" in caplog.text
    db_session.refresh(run)
    assert run.model_dump() == before
    for resolver, expected in zip(resolvers, old_metrics):
        assert [
            row.model_dump()
            for row in resolver.get_all_by_evaluation_run_id(
                session=db_session, evaluation_run_id=run.id
            )
        ] == expected


def test_recompute_evaluation_run__process_exit_preserves_results(tmp_path: Path) -> None:
    engine_url = f"duckdb:///{tmp_path / 'evaluation.duckdb'}"
    engine = DatabaseEngine(engine_url=engine_url, single_threaded=True)
    resolvers = (evaluation_sample_metric_resolver, evaluation_annotation_metric_resolver)
    with engine.session() as session:
        root = helpers.create_dataset_with_annotations(session)
        result = evaluation_service.run_evaluation(
            session=session,
            collection=root,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=ObjectDetectionEvaluationConfig(),
            name="original",
        )
        run = evaluation_run_resolver.get_by_id(
            session=session, evaluation_id=result.evaluation_run_id
        )
        assert run is not None
        before = run.model_dump()
        old_metrics = [
            [
                row.model_dump()
                for row in resolver.get_all_by_evaluation_run_id(
                    session=session, evaluation_run_id=run.id
                )
            ]
            for resolver in resolvers
        ]
    engine.close()
    # Exit after batch writers commit, bypassing all Python cleanup and error recovery.
    crashed = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
import sys
from uuid import UUID
from lightly_studio.database.db_manager import DatabaseEngine
from lightly_studio.evaluation import object_detection_metric
from lightly_studio.resolvers import evaluation_run_resolver
from lightly_studio.services import evaluation_service
persist = object_detection_metric.create_and_persist_object_detection_metrics_per_sample

def crash(**kwargs):
    persist(**kwargs)
    os._exit(23)

object_detection_metric.create_and_persist_object_detection_metrics_per_sample = crash
engine = DatabaseEngine(engine_url=sys.argv[1], single_threaded=True)
with engine.session() as session:
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=UUID(sys.argv[2]))
    evaluation_service.recompute_evaluation_run(session=session, run=run)
""",
            engine_url,
            str(result.evaluation_run_id),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert crashed.returncode == 23, crashed.stderr
    engine = DatabaseEngine(engine_url=engine_url, single_threaded=True)
    try:
        with engine.session() as session:
            run = evaluation_run_resolver.get_by_id(
                session=session, evaluation_id=result.evaluation_run_id
            )
            assert run is not None
            assert run.model_dump() == before
            for resolver, expected in zip(resolvers, old_metrics):
                assert [
                    row.model_dump()
                    for row in resolver.get_all_by_evaluation_run_id(
                        session=session, evaluation_run_id=run.id
                    )
                ] == expected
    finally:
        engine.close()
