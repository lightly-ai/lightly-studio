from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
)
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_create_many(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run, image = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    unmatched_pred_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.75,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=unmatched_pred_annotation.sample_id,
            ),
        ],
    )

    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert len(results) == 2
    assert {result.metric_name for result in results} == {"iou", None}
    assert all(result.sample_id == image.sample_id for result in results)


def test_create_many__empty_list_is_noop(db_session: Session) -> None:
    run, _ = evaluation_sample_metric_helpers.create_run_and_image(session=db_session)

    evaluation_annotation_metric_resolver.create_many(session=db_session, records=[])

    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert results == []
