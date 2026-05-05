"""Implementation of get_sample_ids function for annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: AnnotationsFilter | None = None,
) -> set[UUID]:
    """Get sample IDs for annotations in a given collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to scope results to.
        filters: The annotation filters to apply.

    Returns:
        Set of annotation sample ids matching the given filters.
    """
    query = select(AnnotationBaseTable.sample_id).join(AnnotationBaseTable.sample)
    query = query.where(col(SampleTable.collection_id) == collection_id)
    if filters is not None:
        query = filters.apply(query)
    sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)
