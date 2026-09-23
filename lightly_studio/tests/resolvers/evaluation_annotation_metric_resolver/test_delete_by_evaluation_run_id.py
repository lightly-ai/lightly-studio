from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
)
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_delete_by_evaluation_run_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    pred_annotation, gt_annotation = create_annotations(
        session=db_session,
        collection_id=dataset.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
        ],
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
        ],
    )

    evaluation_annotation_metric_resolver.delete_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )

    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )
    assert results == []


def test_delete_by_evaluation_run_id__does_not_affect_other_runs(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run_to_delete = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_delete"
    )
    run_to_keep = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_keep"
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    pred_annotation, gt_annotation = create_annotations(
        session=db_session,
        collection_id=dataset.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_to_delete.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.5,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_to_keep.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.9,
            ),
        ],
    )

    evaluation_annotation_metric_resolver.delete_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_delete.id
    )

    deleted_results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_delete.id
    )
    assert deleted_results == []

    kept_results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_keep.id
    )
    assert len(kept_results) == 1
    assert kept_results[0].value == pytest.approx(0.9)
