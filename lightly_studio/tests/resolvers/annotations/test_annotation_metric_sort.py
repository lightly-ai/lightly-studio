from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_sort import AnnotationEvaluationMetricSortExpr
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationSide
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers.annotations import annotation_metric_sort
from tests.resolvers.evaluation_sample_metric_resolver import helpers as evaluation_run_helpers


def _unpersisted_run(
    *, gt_annotation_collection_id: UUID, pred_annotation_collection_id: UUID
) -> EvaluationRunTable:
    return EvaluationRunTable(
        name="test_run",
        gt_annotation_collection_id=gt_annotation_collection_id,
        pred_annotation_collection_id=pred_annotation_collection_id,
        dataset_id=uuid4(),
        task_type=EvaluationTaskType.OBJECT_DETECTION,
    )


def test_sort_expr_to_order_by__unknown_run_raises(db_session: Session) -> None:
    sort_expr = AnnotationEvaluationMetricSortExpr(
        evaluation_run_id=uuid4(),
        metric_name="iou",
        direction=SortDirection.asc,
    )

    with pytest.raises(annotation_metric_sort.EvaluationRunNotFoundError):
        annotation_metric_sort.sort_expr_to_order_by(
            session=db_session,
            annotation_collection_id=uuid4(),
            sort_expr=sort_expr,
            annotation_id_column=col(AnnotationBaseTable.sample_id),
        )


def test_sort_expr_to_order_by__source_not_in_run_raises(db_session: Session) -> None:
    run = evaluation_run_helpers.create_run(session=db_session)
    sort_expr = AnnotationEvaluationMetricSortExpr(
        evaluation_run_id=run.id,
        metric_name="iou",
        direction=SortDirection.asc,
    )

    with pytest.raises(annotation_metric_sort.AnnotationSourceNotInEvaluationRunError):
        annotation_metric_sort.sort_expr_to_order_by(
            session=db_session,
            annotation_collection_id=uuid4(),
            sort_expr=sort_expr,
            annotation_id_column=col(AnnotationBaseTable.sample_id),
        )


def test_sort_expr_to_order_by__descending(db_session: Session) -> None:
    run = evaluation_run_helpers.create_run(session=db_session)
    sort_expr = AnnotationEvaluationMetricSortExpr(
        evaluation_run_id=run.id,
        metric_name="iou",
        direction=SortDirection.desc,
    )

    order_by = annotation_metric_sort.sort_expr_to_order_by(
        session=db_session,
        annotation_collection_id=run.gt_annotation_collection_id,
        sort_expr=sort_expr,
        annotation_id_column=col(AnnotationBaseTable.sample_id),
    )

    assert order_by.ascending is False


def test_resolve_side__ground_truth_source() -> None:
    gt_id, pred_id = uuid4(), uuid4()
    run = _unpersisted_run(gt_annotation_collection_id=gt_id, pred_annotation_collection_id=pred_id)

    side = annotation_metric_sort.resolve_side(run=run, annotation_collection_id=gt_id)

    assert side == EvaluationAnnotationSide.GROUND_TRUTH


def test_resolve_side__prediction_source() -> None:
    gt_id, pred_id = uuid4(), uuid4()
    run = _unpersisted_run(gt_annotation_collection_id=gt_id, pred_annotation_collection_id=pred_id)

    side = annotation_metric_sort.resolve_side(run=run, annotation_collection_id=pred_id)

    assert side == EvaluationAnnotationSide.PREDICTION


def test_resolve_side__neither_source() -> None:
    run = _unpersisted_run(
        gt_annotation_collection_id=uuid4(), pred_annotation_collection_id=uuid4()
    )

    side = annotation_metric_sort.resolve_side(run=run, annotation_collection_id=uuid4())

    assert side is None
