from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
)
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
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


def test_get_object_detection_confusion_matrix__class_only_in_gt(
    db_session: Session,
) -> None:
    """GT contains a class that the predictions never produce.

    The class must still appear on both axes so GT and prediction labels stay
    aligned. The unmatched gt is captured in the synthetic FN column. The
    synthetic FP row is also present even though it has no entries.
    """
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
                gt_annotation_id=gt_b.sample_id,
            ),
        ],
    )

    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert matrix.row_labels == ["class_a", "class_b", NO_GROUND_TRUTH_ROW_LABEL]
    assert matrix.col_labels == ["class_a", "class_b", NO_PREDICTION_COL_LABEL]
    assert matrix.counts == [
        [1, 0, 0],
        [0, 0, 1],
        [0, 0, 0],
    ]


def test_get_object_detection_confusion_matrix__class_only_in_pred(
    db_session: Session,
) -> None:
    """Predictions contain a class the ground truth never has.

    The class must still appear on both axes so GT and prediction labels stay
    aligned. The unmatched prediction is captured in the synthetic FP row. The
    synthetic FN column is also present even though it has no entries.
    """
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
        ],
    )

    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert matrix.row_labels == ["class_a", "class_b", NO_GROUND_TRUTH_ROW_LABEL]
    assert matrix.col_labels == ["class_a", "class_b", NO_PREDICTION_COL_LABEL]
    assert matrix.counts == [
        [1, 0, 0],
        [0, 0, 0],
        [0, 1, 0],
    ]


def test_get_object_detection_confusion_matrix__no_fp_or_fn_keeps_synthetic_axes(
    db_session: Session,
) -> None:
    """All ground truths are matched perfectly with no extras on either side.

    The synthetic FP row and FN column must still be present (zero-filled) so
    that callers can rely on a stable axis layout.
    """
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
    gt_a = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_a.annotation_label_id,
    )
    pred_a = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_a.annotation_label_id,
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
        ],
    )

    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert matrix.row_labels == ["class_a", NO_GROUND_TRUTH_ROW_LABEL]
    assert matrix.col_labels == ["class_a", NO_PREDICTION_COL_LABEL]
    assert matrix.counts == [
        [1, 0],
        [0, 0],
    ]


def test_get_object_detection_confusion_matrix__unknown_run(
    db_session: Session,
) -> None:
    matrix = evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )
    assert matrix.row_labels == []
