"""Tests for delete_annotation service method."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services.annotations_service.delete_annotation import (
    delete_annotation,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_annotation__success(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test successful deletion of an existing annotation."""
    # Get an existing annotation
    annotations = annotation_resolver.get_all(session=db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.sample_id

    # Verify annotation exists before deletion
    assert (
        annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id) is not None
    )

    # Delete the annotation
    delete_annotation(session=db_session, annotation_id=annotation_id)

    # Verify annotation was deleted
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id) is None


def test_delete_annotation__raises_error_when_annotation_not_found(
    db_session: Session,
) -> None:
    """Test that delete_annotation raises ValueError when annotation is not found."""
    non_existent_annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    # Call the service and expect ValueError
    with pytest.raises(ValueError, match=f"Annotation {non_existent_annotation_id} not found"):
        delete_annotation(session=db_session, annotation_id=non_existent_annotation_id)


def test_delete_annotation_marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
    )
    gt_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="gt",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
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

    delete_annotation(session=db_session, annotation_id=annotation.sample_id)

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
