"""Tests for delete_annotations service method."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_annotations__marks_evaluation_run_stale(db_session: Session) -> None:
    run, annotation = _create_run_with_gt_annotation(session=db_session)
    annotation_id = annotation.sample_id
    assert run.stale_since is None

    deleted_count = annotations_service.delete_annotations(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
        annotation_ids=[annotation_id],
    )

    assert deleted_count == 1
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id) is None
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_delete_annotations__keeps_evaluation_run_fresh_when_nothing_is_deleted(
    db_session: Session,
) -> None:
    run, _ = _create_run_with_gt_annotation(session=db_session)
    unknown_id = UUID("12345678-1234-5678-1234-567812345678")

    deleted_count = annotations_service.delete_annotations(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
        annotation_ids=[unknown_id],
    )

    assert deleted_count == 0
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is None


def _create_run_with_gt_annotation(
    session: Session,
) -> tuple[EvaluationRunTable, AnnotationBaseTable]:
    image_collection = create_collection(session=session)
    image = create_image(session=session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
    )
    gt_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name="gt",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
    )
    run = evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=image_collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    return run, annotation
