"""Delete annotations by ID and mark affected evaluation runs stale."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_run_resolver,
    sample_resolver,
)


def delete_annotations_by_ids(session: Session, annotation_ids: Sequence[UUID]) -> int:
    """Delete annotations and mark the evaluation runs of their collections stale.

    Args:
        session: Database session.
        annotation_ids: IDs of the annotations to delete. IDs that do not exist are ignored.

    Returns:
        The number of deleted annotations.
    """
    annotation_collection_ids = {
        sample.collection_id
        for sample in sample_resolver.get_many_by_id(
            session=session, sample_ids=list(annotation_ids)
        )
    }
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=annotation_ids
    )
    for annotation_collection_id in annotation_collection_ids:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
    return deleted_count
