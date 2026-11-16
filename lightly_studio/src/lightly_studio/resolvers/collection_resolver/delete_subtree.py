"""Delete a collection with its samples and its descendant collections."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.sample_resolver import sample_dependent_tables


def delete_subtree(session: Session, collection_id: UUID) -> int:
    """Delete a collection, its samples and every descendant collection.

    The annotations of a collection go through ``annotation_resolver.delete_annotations_by_ids``.
    The other samples lose the rows of ``SAMPLE_DEPENDENT_TABLES``. The rows of the sample type
    tables, for example image or video, stay, so a collection with these samples needs
    ``dataset_resolver.delete_dataset``. The delete commits several times and is not atomic,
    see ``annotation_resolver.delete_annotations_by_ids``. Every step is safe to run again.

    Example:
        ``predictions`` is an annotation source that has a caption of a caption below it:

        ```text
        predictions (annotation)
        └── caption (caption)
            └── caption (caption)
        ```

        ```python
        count = collection_resolver.delete_subtree(session=session, collection_id=predictions_id)
        ```

        The delete empties and removes the deepest caption collection first and ``predictions``
        last. ``count`` is the number of annotations that ``predictions`` holds.

    Args:
        session: Database session.
        collection_id: ID of the root collection of the subtree.

    Returns:
        The number of deleted annotations.
    """
    # TODO(Gabriel, 11/2026): Run the delete in one transaction on PostgreSQL, like
    # delete_dataset.py. A caption, evaluation run or annotation that is created after the
    # caller validated the collection can make the delete fail after earlier steps are
    # committed. DuckDB needs the commits, so every step stays safe to run again there.
    subtree = collection_resolver.get_subtree(session=session, collection_id=collection_id)
    subtree_ids = [collection.collection_id for collection in subtree]
    deleted_annotation_count = 0
    # Reversed order: a collection comes after the descendants that reference it.
    for subtree_id in reversed(subtree_ids):
        deleted_annotation_count += _delete_collection(session=session, collection_id=subtree_id)
    return deleted_annotation_count


def _delete_collection(session: Session, collection_id: UUID) -> int:
    """Delete one collection with its samples, and return the deleted annotation count."""
    deleted_annotation_count = _delete_samples(session=session, collection_id=collection_id)
    collection_resolver.delete_dependent_rows(session=session, collection_id=collection_id)
    # DuckDB rejects the delete of the collection in the transaction that deleted its
    # referencing rows, so commit first.
    session.commit()
    collection_resolver.delete(session=session, collection_id=collection_id)
    return deleted_annotation_count


def _delete_samples(session: Session, collection_id: UUID) -> int:
    """Delete the samples of one collection, and return the deleted annotation count.

    Also deletes a sample without a caption, which ``caption_resolver.delete_caption`` keeps.
    """
    annotation_ids = annotation_resolver.get_sample_ids(
        session=session, collection_id=collection_id
    )
    deleted_annotation_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=list(annotation_ids)
    )
    sample_ids = select(SampleTable.sample_id).where(
        col(SampleTable.collection_id) == collection_id
    )
    for table in sample_dependent_tables.SAMPLE_DEPENDENT_TABLES:
        session.exec(delete(table).where(col(table.sample_id).in_(sample_ids)))
    # DuckDB rejects the delete of a sample in the transaction that deleted its referencing rows.
    session.commit()
    session.exec(delete(SampleTable).where(col(SampleTable.collection_id) == collection_id))
    session.commit()
    return deleted_annotation_count
