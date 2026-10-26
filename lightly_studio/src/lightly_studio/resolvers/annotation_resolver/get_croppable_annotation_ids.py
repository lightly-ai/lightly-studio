"""Query for croppable annotations of an annotation collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers.annotation_resolver import croppable_annotations_query


def get_croppable_annotation_ids(session: Session, annotation_collection_id: UUID) -> list[UUID]:
    """Return IDs of all croppable annotations in the collection.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection to scan.

    Returns:
        Annotation sample IDs, ordered by image path.
    """
    query = croppable_annotations_query.build(annotation_collection_id=annotation_collection_id)
    return list(session.exec(query).all())
