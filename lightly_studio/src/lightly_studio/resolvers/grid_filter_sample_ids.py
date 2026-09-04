"""Resolve grid filters to the sample IDs they match."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.grid_filter import GridFilter
from lightly_studio.resolvers.image_filter import ImageFilter


def build_sample_ids_query(
    session: Session, collection_id: UUID, grid_filter: GridFilter
) -> SelectOfScalar[UUID]:
    """Build a distinct sample-ID query for a grid filter and collection."""
    # Resolve any embedding-plot region selection to concrete sample ids before building
    # the query (the point-in-polygon test needs the session, which `apply` lacks).
    if (
        isinstance(grid_filter, ImageFilter)
        and grid_filter.sample_filter is not None
        and grid_filter.sample_filter.embedding_region is not None
    ):
        grid_filter.sample_filter.region_sample_ids = (
            embedding_region_resolver.get_sample_ids_in_region(
                session=session,
                collection_id=collection_id,
                region=grid_filter.sample_filter.embedding_region,
            )
        )
    elif isinstance(grid_filter, AnnotationsFilter) and grid_filter.embedding_region is not None:
        grid_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=grid_filter.embedding_region,
        )
    return grid_filter.build_sample_ids_query(collection_id=collection_id)
