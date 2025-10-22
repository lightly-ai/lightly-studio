from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import (
    BoundingBoxCoordinates,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import get_annotation_by_type


def test_update_bounding_box__object_detection(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for object detection annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    obj_det_annotation = get_annotation_by_type(annotations, AnnotationType.OBJECT_DETECTION)
    annotation_id = obj_det_annotation.annotation_id

    new_coordinates = BoundingBoxCoordinates(
        x=11,
        y=22,
        width=111,
        height=222,
    )

    # Check if the updated annotation is properly returned.
    updated_annotation = annotation_resolver.update_bounding_box(
        db_session, annotation_id, new_coordinates
    )
    assert updated_annotation.object_detection_details is not None
    assert updated_annotation.object_detection_details.x == 11
    assert updated_annotation.object_detection_details.y == 22
    assert updated_annotation.object_detection_details.width == 111
    assert updated_annotation.object_detection_details.height == 222

    # Verify the change persisted in the database.
    updated_obj_det_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert updated_obj_det_annotation is not None
    assert updated_obj_det_annotation.object_detection_details is not None
    assert updated_obj_det_annotation.object_detection_details.x == 11
    assert updated_obj_det_annotation.object_detection_details.y == 22
    assert updated_obj_det_annotation.object_detection_details.width == 111
    assert updated_obj_det_annotation.object_detection_details.height == 222


def test_update_bounding_box__instance_segmentation(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for instance segmentation annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    inst_segm_annotation = get_annotation_by_type(annotations, AnnotationType.INSTANCE_SEGMENTATION)
    annotation_id = inst_segm_annotation.annotation_id

    new_coordinates = BoundingBoxCoordinates(
        x=11,
        y=22,
        width=111,
        height=222,
    )

    # Check if the updated annotation is properly returned.
    updated_annotation = annotation_resolver.update_bounding_box(
        db_session, annotation_id, new_coordinates
    )
    assert updated_annotation.instance_segmentation_details is not None
    assert updated_annotation.instance_segmentation_details.x == 11
    assert updated_annotation.instance_segmentation_details.y == 22
    assert updated_annotation.instance_segmentation_details.width == 111
    assert updated_annotation.instance_segmentation_details.height == 222

    # Verify the change persisted in the database.
    updated_inst_segm_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert updated_inst_segm_annotation is not None
    assert updated_inst_segm_annotation.instance_segmentation_details is not None
    assert updated_inst_segm_annotation.instance_segmentation_details.x == 11
    assert updated_inst_segm_annotation.instance_segmentation_details.y == 22
    assert updated_inst_segm_annotation.instance_segmentation_details.width == 111
    assert updated_inst_segm_annotation.instance_segmentation_details.height == 222


def test_update_bounding_box__classification(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for classification annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    classification_annotation = annotations[0]
    annotation_id = classification_annotation.annotation_id

    new_coordinates = BoundingBoxCoordinates(
        x=10,
        y=20,
        width=100,
        height=200,
    )

    with pytest.raises(ValueError, match="Annotation type does not support bounding boxes."):
        annotation_resolver.update_bounding_box(db_session, annotation_id, new_coordinates)


def test_update_bounding_box__invalid_annotation_id(
    db_session: Session,
) -> None:
    """Test updating bounding box with an invalid annotation ID."""
    invalid_annotation_id = UUID("00000000-0000-0000-0000-000000000000")
    new_coordinates = BoundingBoxCoordinates(
        x=10,
        y=20,
        width=100,
        height=200,
    )

    with pytest.raises(ValueError, match=f"Annotation with ID {invalid_annotation_id} not found."):
        annotation_resolver.update_bounding_box(db_session, invalid_annotation_id, new_coordinates)
