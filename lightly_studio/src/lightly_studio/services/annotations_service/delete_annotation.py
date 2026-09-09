"""Delete an annotation by its ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver


def delete_annotation(session: Session, annotation_id: UUID) -> None:
    """Delete an annotation by its ID.

    Args:
        session: Database session for executing the operation.
        annotation_id: ID of the annotation to delete.

    Raises:
        ValueError: If the annotation with the given ID is not found.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if annotation is None:
        raise ValueError(f"Annotation {annotation_id} not found")
    collection_id = annotation.annotation_collection_id
    annotation_resolver.delete_annotation(session=session, annotation_id=annotation_id)
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
