from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError, NotFoundError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotation_source_service
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
)


def test_delete_annotation_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt_annotation, pred_annotation = _create_gt_and_pred(
        session=db_session, collection=collection, pred_count=2
    )
    pred_source_id = pred_annotation.annotation_collection_id
    create_embedding_model(session=db_session, collection_id=pred_source_id, set_as_default=True)

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=pred_source_id,
    )

    assert deleted_count == 2
    assert collection_resolver.get_by_id(session=db_session, collection_id=pred_source_id) is None
    assert (
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=pred_source_id
        )
        == []
    )
    assert (
        collection_embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=pred_source_id
        )
        == []
    )
    remaining = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[gt_annotation.parent_sample_id]
    )
    assert [annotation.sample_id for annotation in remaining] == [gt_annotation.sample_id]


def test_delete_annotation_source__empty_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    _, pred_annotation = _create_gt_and_pred(session=db_session, collection=collection)
    pred_source_id = pred_annotation.annotation_collection_id
    annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[pred_annotation.sample_id]
    )

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=pred_source_id,
    )

    assert deleted_count == 0
    assert collection_resolver.get_by_id(session=db_session, collection_id=pred_source_id) is None


def test_delete_annotation_source__other_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    _, pred_annotation = _create_gt_and_pred(session=db_session, collection=collection)

    with pytest.raises(NotFoundError, match="not found"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=other_collection.collection_id,
            annotation_source_id=pred_annotation.annotation_collection_id,
        )


def test_delete_annotation_source__not_an_annotation_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    with pytest.raises(NotFoundError, match="not found"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=collection.collection_id,
        )


def test_delete_annotation_source__used_by_evaluation_run(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt_annotation, pred_annotation = _create_gt_and_pred(session=db_session, collection=collection)
    pred_source_id = pred_annotation.annotation_collection_id
    evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_source_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    with pytest.raises(
        AnnotationSourceInUseError,
        match=r"'predictions' is used by the evaluation runs run_a\. Delete these",
    ):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred_source_id,
        )
    assert annotation_resolver.get_by_id(
        session=db_session, annotation_id=pred_annotation.sample_id
    )


def _create_gt_and_pred(
    session: Session, collection: CollectionTable, pred_count: int = 1
) -> tuple[AnnotationBaseTable, AnnotationBaseTable]:
    """Create one ground truth annotation and pred_count predictions on one image."""
    image = create_image(session=session, collection_id=collection.collection_id)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    gt_annotation = create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[details],
        collection_name="ground_truth",
    )[0]
    pred_annotation = create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[details] * pred_count,
        collection_name="predictions",
    )[0]
    return gt_annotation, pred_annotation
