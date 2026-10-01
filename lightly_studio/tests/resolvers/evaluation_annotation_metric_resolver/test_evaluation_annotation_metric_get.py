from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
)
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    TruePositiveMetricStub,
    create_annotation_metrics,
)


def test_get_all_by_evaluation_run_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    [tp_stub] = create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
            ),
        ],
    )

    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert len(results) == 2
    assert all(result.evaluation_run_id == run.id for result in results)
    assert all(result.sample_id == image.sample_id for result in results)

    tp_result = next(r for r in results if r.metric_name == "iou")
    assert tp_result.gt_annotation_id == tp_stub.gt_annotation_id
    assert tp_result.pred_annotation_id == tp_stub.pred_annotation_id
    assert tp_result.value == pytest.approx(0.75)


def test_get_all_by_evaluation_run_id__returns_empty_for_unknown_run(
    db_session: Session,
) -> None:
    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )

    assert results == []


def test_get_all_by_evaluation_run_id__excludes_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run1"
    )
    image1 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/run1.png",
    )
    run2 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run2"
    )
    image2 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/run2.png",
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_annotation1 = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image1.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_annotation2 = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image2.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run1.id,
                sample_id=image1.sample_id,
                pred_annotation_id=pred_annotation1.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run2.id,
                sample_id=image2.sample_id,
                pred_annotation_id=pred_annotation2.sample_id,
            ),
        ],
    )

    results = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run1.id,
    )

    assert len(results) == 1
    assert results[0].evaluation_run_id == run1.id
    assert results[0].sample_id == image1.sample_id
