"""Delete an annotation by its ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver


def delete_annotation(session: Session, annotation_id: UUID) -> None:
    """Delete an annotation by its ID.

    Args:
        session: Database session for executing the operation.
        annotation_id: ID of the annotation to delete.

    Raises:
        ValueError: If the annotation with the given ID is not found.
    """
    annotation_resolver.delete_annotation(session=session, annotation_id=annotation_id)
