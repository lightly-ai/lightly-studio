"""Steps of the annotation source operations."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver, collection_resolver, sample_resolver


def delete_source(session: Session, source: CollectionTable) -> int:
    """Delete an annotation source with its annotations and the rows that point at it.

    Also deletes the captions of the annotations and their child collections. The caller
    checks that the annotation source is not in use, so all child collections are caption
    collections. The delete commits several times and is not atomic, see
    ``annotation_resolver.delete_annotations_by_ids``.

    Args:
        session: Database session.
        source: The annotation source collection.

    Returns:
        The number of deleted annotations.
    """
    source_id = source.collection_id
    child_ids = [child.collection_id for child in source.children]
    annotation_ids = annotation_resolver.get_sample_ids(session=session, collection_id=source_id)
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=list(annotation_ids)
    )
    # Delete the children first, they reference the annotation source.
    for child_id in child_ids:
        sample_resolver.delete_caption_samples(session=session, collection_id=child_id)
    for collection_id in [*child_ids, source_id]:
        collection_resolver.delete_dependent_rows(session=session, collection_id=collection_id)
        # DuckDB rejects the delete of the collection in the transaction that deleted its
        # referencing rows, so commit first.
        session.commit()
        collection_resolver.delete(session=session, collection_id=collection_id)
    return deleted_count
