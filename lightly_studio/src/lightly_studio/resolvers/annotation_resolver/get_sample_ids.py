"""Implementation of get_sample_ids function for annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def build_sample_ids_query(
    collection_id: UUID,
    filters: AnnotationsFilter | None = None,
) -> SelectOfScalar[UUID]:
    """Build the query selecting distinct annotation sample ids for a collection.

    Args:
        collection_id: The ID of the collection to scope results to.
        filters: The annotation filters to apply.

    Returns:
        A query selecting the distinct annotation sample ids matching the filters.
    """
    return (filters or AnnotationsFilter()).build_sample_ids_query(collection_id=collection_id)


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
    if filters is not None and filters.embedding_region is not None:
        filters.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=filters.embedding_region,
        )
    query = build_sample_ids_query(collection_id=collection_id, filters=filters)
    return set(session.exec(query).all())
