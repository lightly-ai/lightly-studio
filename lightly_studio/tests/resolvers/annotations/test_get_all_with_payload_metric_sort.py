"""Tests for ordering get_all_with_payload by a per-annotation evaluation metric."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, col

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationSide
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    FalsePositiveMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)

METRIC_NAME = "iou"
# Exactly representable as a 32-bit float, so it round-trips through the value column.
MATCHED_VALUE = 0.75


@dataclass
class _AnnotationEvaluationMetricFixture:
    """One evaluation run holding every state the ordering has to distinguish."""

    run_id: UUID
    gt_collection_id: UUID
    root_collection_id: UUID
    matched: UUID
    unmatched: UUID
    uncovered: UUID


def test_get_all_with_payload__orders_by_annotation_evaluation_metric__ascending(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(collection_ids=[fixture.gt_collection_id]),
        ordering=annotation_resolver.AnnotationOrdering(
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=fixture.run_id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            )
        ),
    )

    # Unmatched orders as 0.0 ahead of the matched value; uncovered orders last. The
    # count also proves the run's prediction-side annotation was not joined in.
    assert [a.annotation.sample_id for a in annotations_page.annotations] == [
        fixture.unmatched,
        fixture.matched,
        fixture.uncovered,
    ]
    assert annotations_page.total_count == 3


def test_get_all_with_payload__orders_by_annotation_evaluation_metric__descending(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(collection_ids=[fixture.gt_collection_id]),
        ordering=annotation_resolver.AnnotationOrdering(
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=fixture.run_id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            ).desc()
        ),
    )

    # Uncovered stays last in both directions.
    assert [a.annotation.sample_id for a in annotations_page.annotations] == [
        fixture.matched,
        fixture.unmatched,
        fixture.uncovered,
    ]


def test_get_all_with_payload__orders_by_annotation_evaluation_metric__sets_order_value(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(collection_ids=[fixture.gt_collection_id]),
        ordering=annotation_resolver.AnnotationOrdering(
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=fixture.run_id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            )
        ),
    )

    # The unmatched annotation has a metric row without a value and reports 0.0, while the
    # annotation the run did not cover has no row at all and reports nothing.
    assert {
        a.annotation.sample_id: a.annotation.order_value for a in annotations_page.annotations
    } == {
        fixture.matched: MATCHED_VALUE,
        fixture.unmatched: 0.0,
        fixture.uncovered: None,
    }


def test_get_all_with_payload__order_value_is_none_without_ordering(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(collection_ids=[fixture.gt_collection_id]),
    )

    assert [a.annotation.order_value for a in annotations_page.annotations] == [None, None, None]


def test_get_all_with_payload__text_embedding_takes_precedence_over_order_by(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        embedding_dimension=2,
        set_as_default=True,
    )
    # Similarity orders these differently than the metric does in either direction, so the
    # expected order only holds if similarity wins.
    for sample_id, embedding in (
        (fixture.uncovered, [1.0, 0.0]),
        (fixture.matched, [0.0, 1.0]),
        (fixture.unmatched, [-1.0, 0.0]),
    ):
        create_sample_embedding(
            session=db_session,
            sample_id=sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=embedding,
        )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(collection_ids=[fixture.gt_collection_id]),
        ordering=annotation_resolver.AnnotationOrdering(
            text_embedding=[1.0, 0.0],
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=fixture.run_id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            ),
        ),
    )

    assert [a.annotation.sample_id for a in annotations_page.annotations] == [
        fixture.uncovered,
        fixture.matched,
        fixture.unmatched,
    ]
    # The ignored sort contributes no value either.
    assert all(a.annotation.order_value is None for a in annotations_page.annotations)


def test_get_all_with_payload__orders_by_annotation_evaluation_metric__composes_with_label_filter(
    db_session: Session,
) -> None:
    fixture = _create_annotation_evaluation_metric_fixture(session=db_session)
    other_label = create_annotation_label(
        session=db_session,
        root_collection_id=fixture.root_collection_id,
        label_name="airplane",
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=fixture.gt_collection_id,
        filters=AnnotationsFilter(
            collection_ids=[fixture.gt_collection_id],
            annotation_label_ids=[other_label.annotation_label_id],
        ),
        ordering=annotation_resolver.AnnotationOrdering(
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=fixture.run_id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            )
        ),
    )

    assert annotations_page.total_count == 0


def test_get_all_with_payload__orders_by_annotation_evaluation_metric__does_not_multiply_rows(
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    image = create_image(session=db_session, collection_id=root.collection_id)
    # Two metrics on one annotation: the join must still yield a single grid row.
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={METRIC_NAME: MATCHED_VALUE, "disagreement": 0.25},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
        filters=AnnotationsFilter(collection_ids=[run.gt_annotation_collection_id]),
        ordering=annotation_resolver.AnnotationOrdering(
            order_by=OrderByAnnotationEvaluationMetricField(
                evaluation_run_id=run.id,
                metric_name=METRIC_NAME,
                side=EvaluationAnnotationSide.GROUND_TRUTH,
                annotation_id_column=col(AnnotationBaseTable.sample_id),
            )
        ),
    )

    assert annotations_page.total_count == 1


def _create_annotation_evaluation_metric_fixture(
    session: Session,
) -> _AnnotationEvaluationMetricFixture:
    root = create_collection(session=session)
    label = create_annotation_label(session=session, root_collection_id=root.collection_id)
    run = create_run(session=session, collection_id=root.collection_id)

    # Distinct file paths, because the parent file path is the leading tiebreaker.
    image_matched = create_image(
        session=session, collection_id=root.collection_id, file_path_abs="/a.png"
    )
    image_unmatched = create_image(
        session=session, collection_id=root.collection_id, file_path_abs="/b.png"
    )
    image_uncovered = create_image(
        session=session, collection_id=root.collection_id, file_path_abs="/c.png"
    )

    matched_stub, unmatched_stub, _unmatched_pred_stub = create_annotation_metrics(
        session=session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_matched.sample_id,
                metrics={METRIC_NAME: MATCHED_VALUE},
                gt_annotation_label_id=label.annotation_label_id,
            ),
            FalseNegativeMetricStub(
                sample_id=image_unmatched.sample_id,
                gt_annotation_label_id=label.annotation_label_id,
            ),
            # The matched pairing's other side: must not leak into ground-truth results.
            FalsePositiveMetricStub(
                sample_id=image_unmatched.sample_id,
                pred_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    gt_collection = collection_resolver.get_by_id(
        session=session, collection_id=run.gt_annotation_collection_id
    )
    assert gt_collection is not None
    uncovered = create_annotation(
        session=session,
        collection_id=root.collection_id,
        sample_id=image_uncovered.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name=gt_collection.name,
    )

    assert matched_stub.gt_annotation_id is not None
    assert unmatched_stub.gt_annotation_id is not None
    return _AnnotationEvaluationMetricFixture(
        run_id=run.id,
        gt_collection_id=run.gt_annotation_collection_id,
        root_collection_id=root.collection_id,
        matched=matched_stub.gt_annotation_id,
        unmatched=unmatched_stub.gt_annotation_id,
        uncovered=uncovered.sample_id,
    )
