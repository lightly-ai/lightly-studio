"""Tests for update_annotation service method."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import (
    annotation_resolver,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import (
    AnnotationUpdate,
)
from tests.conftest import AnnotationsTestData


def test_update_annotation__calls_update_annotation_label(
    db_session: Session,
    dataset_id: UUID,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.sample_id

    # Get a different existing label
    target_label = annotations_test_data.annotation_labels[1]
    target_label_name = target_label.annotation_label_name

    # Spy on the update_annotation_label function call
    with patch(
        "lightly_studio.services.annotations_service.update_annotation_label"
    ) as mock_update_annotation_label:
        # Update the annotation label using the service
        updated_annotation = annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                label_name=target_label_name,
                dataset_id=dataset_id,
            ),
        )

        # Verify the spy was called with correct arguments
        mock_update_annotation_label.assert_called_once_with(
            session=db_session,
            annotation_id=annotation_id,
            label_name=target_label_name,
        )

    assert updated_annotation is not None


def test_update_annotation__raises_error_when_label_name_is_none(
    db_session: Session,
    dataset_id: UUID,
) -> None:
    """Test that update_annotation raises ValueError when label_name is None."""
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    with pytest.raises(ValueError, match="No updates provided for the annotation"):
        annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                label_name=None,
                dataset_id=dataset_id,
            ),
        )
