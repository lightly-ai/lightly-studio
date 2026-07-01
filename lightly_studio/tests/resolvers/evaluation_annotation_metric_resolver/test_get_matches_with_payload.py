from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
    EvaluationMatchSortField,
    EvaluationMatchType,
    EvaluationMatchView,
)
from lightly_studio.models.evaluation_confusion_matrix import ConfusionCell
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_matches_with_payload__orders_by_iou_descending_by_default(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )

    annotations = [
        create_annotation(
            session=db_session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        for _ in range(6)
    ]
    gt_high, pred_high, gt_low, pred_low, pred_fp, gt_fn = annotations

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            # Intentionally not in final order to prove ordering is applied.
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_fn.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_low.sample_id,
                gt_annotation_id=gt_low.sample_id,
                metric_name="iou",
                value=0.6,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_fp.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_high.sample_id,
                gt_annotation_id=gt_high.sample_id,
                metric_name="iou",
                value=0.9,
            ),
        ],
    )

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
    )

    assert result.total_count == 4
    # Default ordering is by descending IoU; only true positives carry an IoU.
    assert result.matches[0].match_type == EvaluationMatchType.TP
    assert result.matches[0].iou == pytest.approx(0.9)
    assert result.matches[1].match_type == EvaluationMatchType.TP
    assert result.matches[1].iou == pytest.approx(0.6)
    # IoU-less rows (FP/FN) are pushed to the end regardless of direction.
    assert result.matches[2].iou is None
    assert result.matches[3].iou is None
    assert {result.matches[2].match_type, result.matches[3].match_type} == {
        EvaluationMatchType.FP,
        EvaluationMatchType.FN,
    }
    # True positive carries both boxes.
    assert result.matches[0].gt_annotation is not None
    assert result.matches[0].pred_annotation is not None
    # Crop payload is populated from the parent image.
    assert result.matches[0].parent_sample_data.sample_id == image.sample_id


def test_get_matches_with_payload__orders_by_confidence_with_missing_last(
    db_session: Session,
) -> None:
    """Sorting by confidence orders by the prediction score, prediction-less last."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    gt_tp = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_tp = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"confidence": 0.9},
    )
    pred_fp = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"confidence": 0.4},
    )
    gt_fn = create_annotation(
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
                pred_annotation_id=pred_fp.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_tp.sample_id,
                gt_annotation_id=gt_tp.sample_id,
                metric_name="iou",
                value=0.7,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_fn.sample_id,
            ),
        ],
    )

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        sort_field=EvaluationMatchSortField.CONFIDENCE,
        sort_direction=SortDirection.desc,
    )

    # Highest-confidence prediction first, then the lower one; the false negative
    # (no prediction, hence no confidence) is pushed to the end.
    assert [match.match_type for match in result.matches] == [
        EvaluationMatchType.TP,
        EvaluationMatchType.FP,
        EvaluationMatchType.FN,
    ]
    assert result.matches[0].pred_annotation is not None
    assert result.matches[0].pred_annotation.confidence == pytest.approx(0.9)
    assert result.matches[1].pred_annotation is not None
    assert result.matches[1].pred_annotation.confidence == pytest.approx(0.4)
    assert result.matches[2].pred_annotation is None


def test_get_matches_with_payload__orders_by_iou_with_missing_last(
    db_session: Session,
) -> None:
    """Sorting by IoU ascending puts the worst TP first and IoU-less rows last."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    annotations = [
        create_annotation(
            session=db_session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        for _ in range(5)
    ]
    gt_high, pred_high, gt_low, pred_low, pred_fp = annotations
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_high.sample_id,
                gt_annotation_id=gt_high.sample_id,
                metric_name="iou",
                value=0.9,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_low.sample_id,
                gt_annotation_id=gt_low.sample_id,
                metric_name="iou",
                value=0.6,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_fp.sample_id,
            ),
        ],
    )

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        sort_field=EvaluationMatchSortField.IOU,
        sort_direction=SortDirection.asc,
    )

    assert [match.match_type for match in result.matches] == [
        EvaluationMatchType.TP,
        EvaluationMatchType.TP,
        EvaluationMatchType.FP,
    ]
    assert result.matches[0].iou == pytest.approx(0.6)
    assert result.matches[1].iou == pytest.approx(0.9)
    assert result.matches[2].iou is None


def test_get_matches_with_payload__filters_by_match_type(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_fp = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    gt_fn = create_annotation(
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
                pred_annotation_id=pred_fp.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_fn.sample_id,
            ),
        ],
    )

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        match_types=[EvaluationMatchType.FP],
    )

    assert result.total_count == 1
    assert len(result.matches) == 1
    assert result.matches[0].match_type == EvaluationMatchType.FP


def test_get_matches_with_payload__filters_by_label_either_side(
    db_session: Session,
) -> None:
    """A class-confusion TP is kept when either its GT or pred label matches."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
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
                pred_annotation_id=pred_b.sample_id,
                gt_annotation_id=gt_a.sample_id,
                metric_name="iou",
                value=0.8,
            ),
        ],
    )

    by_gt = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        annotation_label_ids=[label_a.annotation_label_id],
    )
    by_pred = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        annotation_label_ids=[label_b.annotation_label_id],
    )

    assert by_gt.total_count == 1
    assert by_pred.total_count == 1


def test_get_matches_with_payload__filters_by_confusion_cell(
    db_session: Session,
) -> None:
    """A confusion cell keeps only the matches in its exact gt/pred label pairing.

    Covers all four quadrants: the diagonal (gt == pred), an off-diagonal class
    confusion (gt != pred), the false-positive margin bucket (null gt), and the
    false-negative margin bucket (null pred).
    """
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
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

    def annotation(label_id: UUID) -> AnnotationBaseTable:
        return create_annotation(
            session=db_session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label_id,
        )

    gt_diag, pred_diag = annotation(label_a.annotation_label_id), annotation(
        label_a.annotation_label_id
    )
    gt_off, pred_off = annotation(label_a.annotation_label_id), annotation(
        label_b.annotation_label_id
    )
    pred_fp = annotation(label_b.annotation_label_id)
    gt_fn = annotation(label_a.annotation_label_id)

    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_diag.sample_id,
                pred_annotation_id=pred_diag.sample_id,
                metric_name="iou",
                value=0.9,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_off.sample_id,
                pred_annotation_id=pred_off.sample_id,
                metric_name="iou",
                value=0.7,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_fp.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_fn.sample_id,
            ),
        ],
    )

    def matches_for(cell: ConfusionCell) -> list[EvaluationMatchView]:
        return evaluation_annotation_metric_resolver.get_matches_with_payload(
            session=db_session,
            evaluation_run_id=run.id,
            collection_id=dataset.collection_id,
            confusion_cell=cell,
        ).matches

    diagonal = matches_for(
        ConfusionCell(evaluation_run_id=run.id, gt_label="class_a", pred_label="class_a")
    )
    assert [m.match_type for m in diagonal] == [EvaluationMatchType.TP]
    assert diagonal[0].iou == pytest.approx(0.9)

    off_diagonal = matches_for(
        ConfusionCell(evaluation_run_id=run.id, gt_label="class_a", pred_label="class_b")
    )
    assert [m.match_type for m in off_diagonal] == [EvaluationMatchType.TP]
    assert off_diagonal[0].iou == pytest.approx(0.7)

    fp_bucket = matches_for(
        ConfusionCell(evaluation_run_id=run.id, gt_label=None, pred_label="class_b")
    )
    assert [m.match_type for m in fp_bucket] == [EvaluationMatchType.FP]

    fn_bucket = matches_for(
        ConfusionCell(evaluation_run_id=run.id, gt_label="class_a", pred_label=None)
    )
    assert [m.match_type for m in fn_bucket] == [EvaluationMatchType.FN]


def test_get_matches_with_payload__scopes_by_image_filter_sample_ids(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    other_image = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/other.png",
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_in_scope = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_out_of_scope = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=other_image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_in_scope.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=other_image.sample_id,
                pred_annotation_id=pred_out_of_scope.sample_id,
            ),
        ],
    )

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        image_filter=ImageFilter(sample_filter=SampleFilter(sample_ids=[image.sample_id])),
    )

    assert result.total_count == 1
    assert result.matches[0].parent_sample_data.sample_id == image.sample_id


def test_get_matches_with_payload__paginates(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    records = []
    for _ in range(3):
        pred = create_annotation(
            session=db_session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        records.append(
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred.sample_id,
            )
        )
    evaluation_annotation_metric_resolver.create_many(session=db_session, records=records)

    result = evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=db_session,
        evaluation_run_id=run.id,
        collection_id=dataset.collection_id,
        pagination=Paginated(offset=0, limit=2),
    )

    assert result.total_count == 3
    assert len(result.matches) == 2
    assert result.next_cursor == 2
