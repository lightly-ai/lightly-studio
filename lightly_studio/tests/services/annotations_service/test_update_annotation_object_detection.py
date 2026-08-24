"""Tests for updating bounding box of object detection annotation."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.services import (
    annotations_service,
)
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from lightly_studio.services.annotations_service.update_annotation_bounding_box import (
    update_annotation_bounding_box,
)
from tests.conftest import AnnotationsTestData, assert_contains_properties
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_annotation_object_detection(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating annotation object detection bounding box."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    object_detection_annotation = annotations.annotations[3]

    assert object_detection_annotation.annotation_type == "object_detection"
    annotation_id = object_detection_annotation.sample_id

    bounding_box = {"x": 11, "y": 21, "width": 201, "height": 202}
    # Update the annotation label using the service
    updated_annotation = annotations_service.update_annotation(
        db_session,
        AnnotationUpdate(
            collection_id=object_detection_annotation.sample.collection_id,
            annotation_id=annotation_id,
            bounding_box=BoundingBoxCoordinates(
                x=bounding_box["x"],
                y=bounding_box["y"],
                width=bounding_box["width"],
                height=bounding_box["height"],
            ),
        ),
    )

    # Verify the annotation was updated correctly
    assert updated_annotation.sample_id == annotation_id

    # Verify the change persisted in the database
    persisted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert persisted_annotation is not None
    assert_contains_properties(
        updated_annotation.object_detection_details,
        {
            "x": bounding_box["x"],
            "y": bounding_box["y"],
            "width": bounding_box["width"],
            "height": bounding_box["height"],
        },
    )


def test_update_annotation_bounding_box_marks_evaluation_run_stale(db_session: Session) -> None:
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

    update_annotation_bounding_box(
        session=db_session,
        annotation_id=annotation.sample_id,
        bounding_box=BoundingBoxCoordinates(x=1, y=2, width=3, height=4),
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
