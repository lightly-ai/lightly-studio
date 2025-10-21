"""Tests for updating annotation labels."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_resolver
from tests.conftest import AnnotationsTestData, assert_contains_properties


def test_update_annotation_label_classification(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    first_annotation = annotations[0]
    annotation_id = first_annotation.annotation_id
    current_annotation_label_id = first_annotation.annotation_label_id
    new_label = annotations_test_data.annotation_labels[1]

    assert current_annotation_label_id != new_label.annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_label.annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None
    assert (
        updated_annotation.annotation_label.annotation_label_name == new_label.annotation_label_name
    )


def test_update_annotation_with_tags(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
    annotation_tags_assigned: list[TagTable],  # noqa: ARG001
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = annotations[0]
    annotation_id = annotation.annotation_id
    current_annotation_label_id = annotation.annotation_label_id
    new_label = annotations_test_data.annotation_labels[1]
    existing_tags = [tag.tag_id for tag in annotation.tags]

    assert current_annotation_label_id != new_label.annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_label.annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None

    tags = [tag.tag_id for tag in updated_annotation.tags]
    assert tags == existing_tags


def test_update_annotation_label_object_detection(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating object detection annotation label."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = annotations[3]

    current_annotation_label_id = annotation.annotation_label_id
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    assert annotation.object_detection_details

    x = annotation.object_detection_details.x
    y = annotation.object_detection_details.y
    width = annotation.object_detection_details.width
    height = annotation.object_detection_details.height

    assert annotation.object_detection_details is not None
    assert current_annotation_label_id != new_annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation.annotation_id,
        new_annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation.annotation_id)

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_annotation_label_id

    assert_contains_properties(
        updated_annotation.object_detection_details,
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
    )


def test_update_annotation_label_instance_segmentation(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = annotations[6]
    annotation_id = annotation.annotation_id
    current_annotation_label_id = annotation.annotation_label_id
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    assert annotation.instance_segmentation_details
    x = annotation.instance_segmentation_details.x
    y = annotation.instance_segmentation_details.y
    width = annotation.instance_segmentation_details.width
    height = annotation.instance_segmentation_details.height
    segmentation_mask = annotation.instance_segmentation_details.segmentation_mask

    assert current_annotation_label_id != new_annotation_label_id
    assert annotation.instance_segmentation_details is not None

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_annotation_label_id
    assert_contains_properties(
        updated_annotation.instance_segmentation_details,
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "segmentation_mask": segmentation_mask,
        },
    )


def test_update_annotation_label_semantic_segmentation(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = annotations[9]
    annotation_id = annotation.annotation_id
    current_annotation_label_id = annotation.annotation_label_id
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    assert annotation.semantic_segmentation_details
    segmentation_mask = annotation.semantic_segmentation_details.segmentation_mask

    assert current_annotation_label_id != new_annotation_label_id
    assert annotation.semantic_segmentation_details is not None

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_annotation_label_id
    assert_contains_properties(
        updated_annotation.semantic_segmentation_details,
        {
            "segmentation_mask": segmentation_mask,
        },
    )


def test_update_annotation_label_raise_error_on_wrong_annotation_id(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test for wrong annotation_id."""
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    with pytest.raises(ValueError, match=f"Annotation with ID {annotation_id} not found."):
        annotation_resolver.update_annotation_label(
            db_session,
            annotation_id,
            new_annotation_label_id,
        )
