"""Tests for update_annotation_label service method."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import (
    annotation_resolver,
)
from lightly_studio.services.annotations_service.update_annotation_label import (
    update_annotation_label,
)
from tests.conftest import AnnotationsTestData


def test_update_annotation_label_with_existing_label(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation label."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.annotation_id

    # Get a different existing label
    target_label = annotations_test_data.annotation_labels[1]
    target_label_name = target_label.annotation_label_name

    # Update the annotation label using the service
    updated_annotation = update_annotation_label(db_session, annotation_id, target_label_name)

    # Verify the annotation was updated correctly
    assert updated_annotation.annotation_id == annotation_id
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
    annotation_id = first_annotation.annotation_id

    # Define a new label name that does not exist
    new_label_name = "New Label"

    # Update the annotation label using the service
    updated_annotation = update_annotation_label(db_session, annotation_id, new_label_name)

    # Verify the annotation was updated correctly
    assert updated_annotation.annotation_id == annotation_id

    # Verify the change persisted in the database
    persisted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert persisted_annotation is not None
    assert persisted_annotation.annotation_label.annotation_label_name == new_label_name
