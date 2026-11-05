"""Delete an annotation source with all its annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.services.annotation_source_service import checks, get_annotation_source, steps


def delete_annotation_source(
    session: Session, dataset_collection_id: UUID, annotation_source_id: UUID
) -> int:
    """Delete an annotation source, its annotations and the rows that point at it.

    The delete is not atomic, see ``annotation_resolver.delete_annotations_by_ids``.

    Args:
        session: Database session.
        dataset_collection_id: ID of the collection that owns the annotation source.
        annotation_source_id: ID of the annotation source collection.

    Returns:
        The number of deleted annotations.

    Raises:
        NotFoundError: If the collection has no annotation source with this ID.
        AnnotationSourceInUseError: If evaluation runs use the annotation source or it has
            child collections.
    """
    source = get_annotation_source.get_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    checks.check_not_in_use(session=session, source=source)
    return steps.delete_source(session=session, source_id=annotation_source_id)
