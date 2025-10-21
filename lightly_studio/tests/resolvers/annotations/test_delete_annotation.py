from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver
from tests.conftest import AnnotationsTestData


def test_delete_annotation__success(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test deleting an annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations

    annotation_ids_to_delete = [
        annotations[0].annotation_id,  # classification
        annotations[3].annotation_id,  # object detection
        annotations[6].annotation_id,  # instance segmentation
        annotations[9].annotation_id,  # semantic segmentation
    ]

    for annotation_id in annotation_ids_to_delete:
        annotation_resolver.delete_annotation(db_session, annotation_id)

        # Verify the change persisted in the database.
        deleted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
        assert deleted_annotation is None


def test_delete_annotation__raises_error_when_annotation_not_found(
    db_session: Session,
) -> None:
    """Test that delete_annotation raises ValueError when annotation is not found."""
    non_existent_annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    # Call the resolver and expect ValueError
    with pytest.raises(ValueError, match=f"Annotation {non_existent_annotation_id} not found"):
        annotation_resolver.delete_annotation(db_session, non_existent_annotation_id)
