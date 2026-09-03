"""Server-side resolution of a grid filter's embedding-plot region selection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.resolvers.image_filter import ImageFilter


def resolve_region_sample_ids(
    session: Session, collection_id: UUID, grid_filter: GridFilterBase
) -> None:
    """Replace a region selection on ``grid_filter`` with the sample ids it covers.

    The point-in-polygon test needs a session, which ``GridFilterBase.apply`` does not
    have. Callers must therefore run this before building a query from the filter.
    The filter is updated in place.

    Args:
        session: Database session.
        collection_id: ID of the collection the region selection was made in.
        grid_filter: The filter to resolve the region of. Filters without a region
            selection are left untouched.
    """
    if isinstance(grid_filter, AnnotationsFilter):
        if grid_filter.embedding_region is None:
            return
        grid_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=grid_filter.embedding_region,
        )
        return

    if not isinstance(grid_filter, ImageFilter):
        return
    sample_filter = grid_filter.sample_filter
    if sample_filter is None or sample_filter.embedding_region is None:
        return
    sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )
