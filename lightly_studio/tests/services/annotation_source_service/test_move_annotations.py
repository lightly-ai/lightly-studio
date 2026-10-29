from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.errors import NotFoundError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    evaluation_run_resolver,
    sample_embedding_resolver,
)
from lightly_studio.services import annotation_source_service
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_move_annotations__existing_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt_annotation, pred_annotations = _create_gt_and_preds(
        session=db_session, collection=collection, pred_count=2
    )
    pred_source_id = pred_annotations[0].annotation_collection_id
    gt_source_id = gt_annotation.annotation_collection_id

    target_id, moved_count = annotation_source_service.move_annotations(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_ids=[pred_annotations[0].sample_id],
        target_annotation_source_name="ground_truth",
    )

    assert (target_id, moved_count) == (gt_source_id, 1)
    moved = annotation_resolver.get_by_id(
        session=db_session, annotation_id=pred_annotations[0].sample_id
    )
    assert moved is not None
    assert moved.annotation_collection_id == gt_source_id
    kept = annotation_resolver.get_by_id(
        session=db_session, annotation_id=pred_annotations[1].sample_id
    )
    assert kept is not None
    assert kept.annotation_collection_id == pred_source_id
    # The old source keeps its coverage of the image.
    parent_id = gt_annotation.parent_sample_id
    for source_id in (gt_source_id, pred_source_id):
        assert annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=source_id
        ) == [parent_id]


def test_move_annotations__new_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    _, pred_annotations = _create_gt_and_preds(session=db_session, collection=collection)
    pred = pred_annotations[0]

    target_id, moved_count = annotation_source_service.move_annotations(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_ids=[pred.sample_id],
        target_annotation_source_name="reviewed",
    )

    assert moved_count == 1
    assert (
        collection_resolver.get_by_name(
            session=db_session, name="reviewed", parent_collection_id=collection.collection_id
        )
        == target_id
    )
    assert annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=target_id
    ) == [pred.parent_sample_id]


def test_move_annotations__keeps_embeddings_and_links_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    _, pred_annotations = _create_gt_and_preds(session=db_session, collection=collection)
    pred = pred_annotations[0]
    model = create_embedding_model(
        session=db_session, collection_id=pred.annotation_collection_id, set_as_default=True
    )
    create_sample_embedding(
        session=db_session,
        sample_id=pred.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0] * 128,
    )

    target_id, _ = annotation_source_service.move_annotations(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_ids=[pred.sample_id],
        target_annotation_source_name="reviewed",
    )

    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=target_id
        )
        == model.embedding_model_id
    )
    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=[pred.sample_id], embedding_model_id=model.embedding_model_id
    )
    assert len(embeddings) == 1


def test_move_annotations__marks_evaluation_runs_stale(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt_annotation, pred_annotations = _create_gt_and_preds(
        session=db_session, collection=collection
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_annotations[0].annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    annotation_source_service.move_annotations(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_ids=[pred_annotations[0].sample_id],
        target_annotation_source_name="reviewed",
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_move_annotations__already_in_target(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt_annotation, _ = _create_gt_and_preds(session=db_session, collection=collection)

    _, moved_count = annotation_source_service.move_annotations(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_ids=[gt_annotation.sample_id],
        target_annotation_source_name="ground_truth",
    )

    assert moved_count == 0


def test_move_annotations__other_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    gt_annotation, _ = _create_gt_and_preds(session=db_session, collection=collection)

    with pytest.raises(NotFoundError, match="not found"):
        annotation_source_service.move_annotations(
            session=db_session,
            dataset_collection_id=other_collection.collection_id,
            annotation_ids=[gt_annotation.sample_id],
            target_annotation_source_name="reviewed",
        )


def _create_gt_and_preds(
    session: Session, collection: CollectionTable, pred_count: int = 1
) -> tuple[AnnotationBaseTable, list[AnnotationBaseTable]]:
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
    pred_annotations = create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[details] * pred_count,
        collection_name="predictions",
    )
    return gt_annotation, pred_annotations
