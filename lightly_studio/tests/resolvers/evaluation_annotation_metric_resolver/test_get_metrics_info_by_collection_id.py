from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricInfoView,
    EvaluationRunAnnotationMetricsInfoView,
)
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)


def test_get_metrics_info_by_collection_id__ground_truth_side(db_session: Session) -> None:
    run = _create_run_with_metrics(session=db_session)
    expected = [
        EvaluationRunAnnotationMetricsInfoView(
            run_id=run.id,
            run_name="detection eval",
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            metrics=[
                EvaluationAnnotationMetricInfoView(metric_name="disagreement"),
                EvaluationAnnotationMetricInfoView(metric_name="iou"),
            ],
        )
    ]

    info = evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
    )

    assert info == expected


def test_get_metrics_info_by_collection_id__prediction_side(db_session: Session) -> None:
    run = _create_run_with_metrics(session=db_session)
    expected = [
        EvaluationRunAnnotationMetricsInfoView(
            run_id=run.id,
            run_name="detection eval",
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            metrics=[
                EvaluationAnnotationMetricInfoView(metric_name="disagreement"),
                EvaluationAnnotationMetricInfoView(metric_name="iou"),
            ],
        )
    ]

    info = evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=db_session,
        collection_id=run.pred_annotation_collection_id,
    )

    assert info == expected


def test_get_metrics_info_by_collection_id__omits_run_without_metric_names(
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    image = create_image(session=db_session, collection_id=root.collection_id)
    # A false negative writes a row carrying no metric name, which is not a sort option.
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            FalseNegativeMetricStub(
                sample_id=image.sample_id,
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    info = evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
    )

    assert info == []


def test_get_metrics_info_by_collection_id__omits_run_without_annotation_metrics(
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    run = create_run(session=db_session, collection_id=root.collection_id)

    info = evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
    )

    assert info == []


def test_get_metrics_info_by_collection_id__omits_run_of_other_source(
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    other_run = create_run(session=db_session, collection_id=root.collection_id, name="other run")
    image = create_image(session=db_session, collection_id=root.collection_id)
    create_annotation_metrics(
        session=db_session,
        run_id=other_run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    info = evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
    )

    assert info == []


def _create_run_with_metrics(session: Session) -> EvaluationRunTable:
    root = create_collection(session=session)
    label = create_annotation_label(session=session, root_collection_id=root.collection_id)
    run = create_run(session=session, collection_id=root.collection_id, name="detection eval")
    image = create_image(session=session, collection_id=root.collection_id)
    create_annotation_metrics(
        session=session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75, "disagreement": 0.25},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )
    return run
