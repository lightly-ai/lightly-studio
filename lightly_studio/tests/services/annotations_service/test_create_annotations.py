from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image


def test_create_annotations(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )

    annotation_ids = annotations_service.create_annotations(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                parent_sample_id=image.sample_id,
            )
            for label in (cat, dog)
        ],
        collection_name="gt",
        covered_sample_ids=[],
    )

    annotations = annotation_resolver.get_by_ids(session=db_session, annotation_ids=annotation_ids)
    assert [a.annotation_label.annotation_label_name for a in annotations] == ["cat", "dog"]
    assert {a.sample.collection.name for a in annotations} == {"gt"}


def test_create_annotations__invalid_annotation(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    detection_without_box = AnnotationCreate(
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        parent_sample_id=image.sample_id,
    )

    with pytest.raises(ValueError, match=r"Missing x or y"):
        annotations_service.create_annotations(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[detection_without_box],
            collection_name="gt",
            covered_sample_ids=[],
        )

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[image.sample_id]
    )
    assert annotations == []


def test_create_annotations__marks_evaluation_run_stale(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    run = _create_evaluation_run(session=db_session, collection=collection, gt_name="gt")

    annotations_service.create_annotations(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                parent_sample_id=image.sample_id,
            )
        ],
        collection_name="gt",
        covered_sample_ids=[],
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_create_annotations__covered_samples_without_annotations(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    run = _create_evaluation_run(session=db_session, collection=collection, gt_name="gt")

    annotation_ids = annotations_service.create_annotations(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[],
        collection_name="gt",
        covered_sample_ids=[image.sample_id],
    )

    gt_collection_id = collection_resolver.get_by_name(
        session=db_session, name="gt", parent_collection_id=collection.collection_id
    )
    assert gt_collection_id is not None
    covered_sample_ids = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=gt_collection_id
    )
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert annotation_ids == []
    assert covered_sample_ids == [image.sample_id]
    assert refreshed is not None
    assert refreshed.stale_since is None


def _create_evaluation_run(
    session: Session, collection: CollectionTable, gt_name: str
) -> EvaluationRunTable:
    gt_collection = create_collection(
        session=session,
        collection_name=gt_name,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection.collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection.collection_id,
    )
    return evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )
