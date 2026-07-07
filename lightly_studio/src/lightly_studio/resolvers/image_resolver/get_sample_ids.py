"""Implementation of get_sample_ids function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def build_sample_ids_query(
    collection_id: UUID,
    filters: ImageFilter | None = None,
) -> SelectOfScalar[UUID]:
    """Build the query selecting distinct sample ids for a given collection.

    Args:
        collection_id: The ID of the collection to scope results to.
        filters: The image filters to apply.

    Returns:
        A query selecting the distinct sample ids matching the given filters.
    """
    return (filters or ImageFilter()).build_sample_ids_query(collection_id=collection_id)


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None = None,
) -> set[UUID]:
    """Get sample IDs for a given collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to scope results to.
        filters: The image filters to apply.

    Returns:
        List of sample ids matching the given filters.
    """
    # Resolve any embedding-plot region selection to concrete sample ids on the filter before the
    # query is built (the point-in-polygon test needs the session, which `apply` lacks).
    sample_filter = filters.sample_filter if filters is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    query = build_sample_ids_query(collection_id=collection_id, filters=filters)
    return set(session.exec(query).all())
