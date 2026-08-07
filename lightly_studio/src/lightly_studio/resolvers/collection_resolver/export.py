"""Resolver functions for exporting collection samples based on filters."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


# TODO(Michal, 10/2025): Consider moving the export logic to a separate service.
# This is a legacy code from the initial implementation of the export feature.
def export(
    session: Session,
    collection_id: UUID,
    collection_filter: ImageFilter | None = None,
) -> list[str]:
    # TODO(lukas, 03/2026): take dataset_id instead of collection_id
    """Retrieve samples for exporting from a collection.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        collection_filter: Active view filter for selecting samples to export.

    Returns:
        List of file paths
    """
    # Resolve any embedding-plot region selection to concrete sample ids before the query is
    # built (the point-in-polygon test needs the session, which `_build_export_query` lacks).
    sample_filter = collection_filter.sample_filter if collection_filter is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    query = _build_export_query(
        collection_id=collection_id,
        collection_filter=collection_filter,
    )
    result = session.exec(query).all()
    return [sample.file_path_abs for sample in result]


def get_filtered_samples_count(
    session: Session,
    collection_id: UUID,
    collection_filter: ImageFilter | None = None,
) -> int:
    # TODO(lukas, 03/2026): take dataset_id instead of collection_id
    """Get statistics about the export query.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        collection_filter: Active view filter for selecting samples to export.

    Returns:
        Count of files to be exported
    """
    # Resolve any embedding-plot region selection to concrete sample ids before the query is
    # built (the point-in-polygon test needs the session, which `_build_export_query` lacks).
    sample_filter = collection_filter.sample_filter if collection_filter is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    query = _build_export_query(
        collection_id=collection_id,
        collection_filter=collection_filter,
    )
    count_query = select(func.count()).select_from(query.subquery())
    return session.exec(count_query).one() or 0


def _build_export_query(
    collection_id: UUID,
    collection_filter: ImageFilter | None = None,
) -> SelectOfScalar[ImageTable]:
    """Build the export query based on the collection filter.

    Args:
        collection_id: UUID of the collection.
        collection_filter: Active view filter applied as an intersection over all samples.

    Returns:
        SQLModel select query
    """
    active_view_subquery = (
        collection_filter.build_sample_ids_query(collection_id)
        if collection_filter is not None
        else None
    )

    query = (
        select(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
        .order_by(col(ImageTable.created_at).asc())
        .distinct()
    )

    if active_view_subquery is not None:
        query = query.where(col(SampleTable.sample_id).in_(active_view_subquery))

    return query
