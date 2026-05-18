from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
)
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
)
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from lightly_studio.resolvers.evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix import (  # noqa: E501
    _label_for_annotation,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_object_detection_confusion_matrix__empty_run(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run, _image = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert matrix.row_labels == []
    assert matrix.col_labels == []
    assert matrix.counts == []


def test_get_object_detection_confusion_matrix__aggregates_tp_fp_fn(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run, image = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    label_a = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
        label_name="class_a",
    )
    label_b = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
        label_name="class_b",
    )
    gt_a = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_a.annotation_label_id,
    )
    gt_b = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_b.annotation_label_id,
    )
    pred_a = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_a.annotation_label_id,
    )
    pred_b = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_b.annotation_label_id,
    )

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_a.sample_id,
                gt_annotation_id=gt_a.sample_id,
                metric_name="iou",
                value=0.9,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_b.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_b.sample_id,
            ),
        ],
    )

    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert matrix.row_labels == [
        "class_a",
        "class_b",
        NO_GROUND_TRUTH_ROW_LABEL,
    ]
    assert matrix.col_labels == [
        "class_a",
        "class_b",
        NO_PREDICTION_COL_LABEL,
    ]
    assert matrix.counts == [
        [1, 0, 0],
        [0, 0, 1],
        [0, 1, 0],
    ]


def test_label_for_annotation__missing_annotation_raises() -> None:
    annotation_id = uuid.uuid4()
    with pytest.raises(RuntimeError, match="non-existent annotation"):
        _label_for_annotation(
            annotation_id,
            annotations_by_id={},
            label_name_by_id={},
        )


def test_label_for_annotation__missing_label_raises() -> None:
    annotation_id = uuid.uuid4()
    label_id = uuid.uuid4()
    fake_annotation = SimpleNamespace(annotation_label_id=label_id)
    with pytest.raises(RuntimeError, match="non-existent label"):
        _label_for_annotation(
            annotation_id,
            annotations_by_id={annotation_id: fake_annotation},  # type: ignore[dict-item]
            label_name_by_id={},
        )


def test_get_object_detection_confusion_matrix__unknown_run(
    db_session: Session,
) -> None:
    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )
    assert matrix.row_labels == []
