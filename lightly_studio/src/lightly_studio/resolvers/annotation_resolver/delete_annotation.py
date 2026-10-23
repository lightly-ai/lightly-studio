"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver


def delete_annotation(
    session: Session,
    annotation_id: UUID,
    delete_sample: bool = True,
) -> None:
    """Delete an annotation and its dependent rows.

    Args:
        session: Database session.
        annotation_id: ID of the annotation to delete.
        delete_sample: Whether to also delete the annotation's sample. Defaults to True.
                      Set to False when updating an annotation (to reuse the sample).

    Raises:
        ValueError: If the annotation does not exist.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation {annotation_id} not found")

    annotation_resolver.delete_annotations_by_ids(
        session=session,
        annotation_ids=[annotation_id],
        delete_samples=delete_sample,
    )
