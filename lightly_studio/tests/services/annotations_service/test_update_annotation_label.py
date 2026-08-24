"""Tests for update_annotation_label service method."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services.annotations_service.update_annotation_label import (
    update_annotation_label,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_annotation_label_with_existing_label(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation label."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.sample_id

    # Get a different existing label
    target_label = annotations_test_data.annotation_labels[1]
    target_label_name = target_label.annotation_label_name

    # Update the annotation label using the service
    updated_annotation = update_annotation_label(db_session, annotation_id, target_label_name)

    # Verify the annotation was updated correctly
    assert updated_annotation.sample_id == annotation_id
    assert updated_annotation.annotation_label_id == target_label.annotation_label_id

    # Verify the change persisted in the database
    persisted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert persisted_annotation is not None
    assert persisted_annotation.annotation_label_id == target_label.annotation_label_id


def test_update_annotation_label_creates_new_label(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating annotation label with a new label."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.sample_id

    # Define a new label name that does not exist
    new_label_name = "New Label"

    # Update the annotation label using the service
    updated_annotation = update_annotation_label(db_session, annotation_id, new_label_name)

    # Verify the annotation was updated correctly
    assert updated_annotation.sample_id == annotation_id

    # Verify the change persisted in the database
    persisted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert persisted_annotation is not None
    assert persisted_annotation.annotation_label.annotation_label_name == new_label_name


def test_update_annotation_label_marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
    )
    pred_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="pred",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=image_collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    update_annotation_label(
        session=db_session,
        annotation_id=annotation.sample_id,
        label_name="dog",
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
