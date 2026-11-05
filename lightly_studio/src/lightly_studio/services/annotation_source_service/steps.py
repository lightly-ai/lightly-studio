"""Steps of the annotation source operations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver, collection_resolver


def delete_source(session: Session, source_id: UUID) -> int:
    """Delete an annotation source with its annotations and the rows that point at it.

    The caller checks that the annotation source is not in use. The delete commits several
    times and is not atomic, see ``annotation_resolver.delete_annotations_by_ids``.

    Returns:
        The number of deleted annotations.
    """
    annotation_ids = annotation_resolver.get_sample_ids(session=session, collection_id=source_id)
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=list(annotation_ids)
    )
    collection_resolver.delete_dependent_rows(session=session, collection_id=source_id)
    # DuckDB rejects the delete of the collection in the transaction that deleted its
    # referencing rows, so commit first.
    session.commit()
    collection_resolver.delete(session=session, collection_id=source_id)
    return deleted_count
