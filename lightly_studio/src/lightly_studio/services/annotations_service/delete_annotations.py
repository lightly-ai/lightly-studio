"""Delete many annotations of one annotation collection by their IDs."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver


def delete_annotations(
    session: Session,
    collection_id: UUID,
    annotation_ids: Sequence[UUID],
) -> int:
    """Delete annotations of an annotation collection and mark its evaluation runs stale.

    Args:
        session: Database session for executing the operation.
        collection_id: ID of the annotation collection that the annotations belong to.
        annotation_ids: IDs of the annotations to delete. IDs that are not in the collection
            are ignored.

    Returns:
        The number of deleted annotations.
    """
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session,
        annotation_collection_id=collection_id,
        annotation_ids=annotation_ids,
    )
    if deleted_count > 0:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session,
            collection_id=collection_id,
        )
    return deleted_count
