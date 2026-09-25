"""Shared helpers for metadata sample resolvers."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlmodel import Session

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.type_definitions import QueryType


def get_merged_schema(session: Session, collection_id: UUID) -> dict[str, str]:
    """Merge the metadata schemas of all samples in a collection."""
    rows = session.exec(
        sqlmodel.select(SampleMetadataTable.metadata_schema)
        .distinct()
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            sqlmodel.col(SampleMetadataTable.sample_id) == sqlmodel.col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    merged: dict[str, str] = {}
    for schema_dict in rows:
        merged.update(schema_dict)
    return merged


def without_metadata_key_filter(
    filters: ImageFilter | VideoFilter | None, metadata_key: str
) -> ImageFilter | VideoFilter | None:
    """Return a copy of ``filters`` without the metadata filters for ``metadata_key``."""
    if (
        filters is None
        or filters.sample_filter is None
        or not filters.sample_filter.metadata_filters
    ):
        return filters
    updated = filters.model_copy(deep=True)
    # Narrowed above via ``filters``; the deep copy preserves both.
    assert updated.sample_filter is not None
    assert updated.sample_filter.metadata_filters is not None
    updated.sample_filter.metadata_filters = [
        metadata_filter
        for metadata_filter in updated.sample_filter.metadata_filters
        if metadata_filter.key != metadata_key
    ]
    return updated


def apply_collection_filter(
    query: QueryType,
    collection_id: UUID,
    filters: ImageFilter | VideoFilter | None,
) -> QueryType:
    """Restrict a query to samples matching ``filters``."""
    if filters is None:
        return query
    filtered_sample_ids = filters.build_sample_ids_query(collection_id=collection_id)
    return query.where(sqlmodel.col(SampleTable.sample_id).in_(filtered_sample_ids))
