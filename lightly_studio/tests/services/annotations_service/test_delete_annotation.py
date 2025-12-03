"""Tests for delete_annotation service method."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver
from lightly_studio.services.annotations_service.delete_annotation import (
    delete_annotation,
)
from tests.conftest import AnnotationsTestData


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
