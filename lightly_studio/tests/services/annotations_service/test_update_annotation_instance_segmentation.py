"""Tests for updating bounding box of annotation instance segmentation."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import (
    annotation_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.services import (
    annotations_service,
)
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from tests.conftest import AnnotationsTestData, assert_contains_properties


def test_update_annotation_instance_segmentation(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating annotation instance segmentation mask."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    instance_segmentation_annotation = annotations.annotations[6]
    annotation_id = instance_segmentation_annotation.annotation_id

    bounding_box = {"x": 11, "y": 21, "width": 201, "height": 202}

    assert instance_segmentation_annotation.annotation_type == "instance_segmentation"

    # Update the annotation label using the service
    updated_annotation = annotations_service.update_annotation(
        db_session,
        AnnotationUpdate(
            dataset_id=instance_segmentation_annotation.dataset_id,
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
    assert updated_annotation.annotation_id == annotation_id

    # Verify the change persisted in the database
    persisted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert persisted_annotation is not None
    assert_contains_properties(
        updated_annotation.instance_segmentation_details,
        {
            "x": bounding_box["x"],
            "y": bounding_box["y"],
            "width": bounding_box["width"],
            "height": bounding_box["height"],
        },
    )
