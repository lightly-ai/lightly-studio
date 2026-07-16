"""Resolver for operations for retrieving metadata info."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Integer, cast, func
from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import (
    HistogramView,
    MetadataInfoView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable

if TYPE_CHECKING:
    from lightly_studio.resolvers.image_filter import ImageFilter
    from lightly_studio.type_definitions import QueryType

# Number of bins used for numeric metadata histograms.
_HISTOGRAM_BIN_COUNT = 20

_NUMERIC_TYPES = ("integer", "float")


def get_all_metadata_keys_and_schema(
    session: Session,
    collection_id: UUID,
) -> list[MetadataInfoView]:
    """Get all unique metadata keys and their schema for a collection.

    For numerical types (``integer`` and ``float``) the returned info also
    contains the min/max values and a value-distribution histogram.

    Args:
        session: The database session.
        collection_id: The collection's UUID.

    Returns:
        List of metadata info objects with 'name', 'type', and, for numerical
        types, 'min', 'max', and 'histogram'.
    """
    merged = _get_merged_schema(session=session, collection_id=collection_id)

    result = []
    for key, metadata_type in merged.items():
        metadata_info = MetadataInfoView(name=key, type=metadata_type)

        # Add min, max, and histogram for numerical types.
        if metadata_type in _NUMERIC_TYPES:
            stats = _get_metadata_min_max_count(
                session=session, collection_id=collection_id, metadata_key=key
            )
            if stats is not None:
                min_value, max_value, _ = stats
                cast_type = int if metadata_type == "integer" else float
                metadata_info.min = cast_type(min_value)
                metadata_info.max = cast_type(max_value)
                metadata_info.histogram = _compute_histogram(
                    session=session,
                    collection_id=collection_id,
                    metadata_key=key,
                    stats=stats,
                )

        result.append(metadata_info)

    return result


def get_metadata_histograms(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    bin_count: int = _HISTOGRAM_BIN_COUNT,
) -> dict[str, HistogramView]:
    """Compute value-distribution histograms for all numeric metadata keys.

    Bin edges always span the full (unfiltered) value range of each key, so
    the chart's x-axis stays stable while the counts change with the active
    filters. Each key's own metadata filter is excluded from its histogram
    (faceted-search behavior): the full shape of the field being adjusted
    stays visible while every other filter applies.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        filters: Optional sample filters restricting which values are counted.
        bin_count: Number of equal-width bins per histogram.

    Returns:
        Mapping of metadata key to its histogram.
    """
    merged = _get_merged_schema(session=session, collection_id=collection_id)

    histograms: dict[str, HistogramView] = {}
    for key, metadata_type in merged.items():
        if metadata_type not in _NUMERIC_TYPES:
            continue
        stats = _get_metadata_min_max_count(
            session=session, collection_id=collection_id, metadata_key=key
        )
        if stats is None:
            continue
        histograms[key] = _compute_histogram(
            session=session,
            collection_id=collection_id,
            metadata_key=key,
            stats=stats,
            filters=_without_metadata_key_filter(filters=filters, metadata_key=key),
            bin_count=bin_count,
        )
    return histograms


def _get_merged_schema(session: Session, collection_id: UUID) -> dict[str, str]:
    """Merge the metadata schemas of all samples in the collection."""
    rows = session.exec(
        select(SampleMetadataTable.metadata_schema)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    merged: dict[str, str] = {}
    for schema_dict in rows:
        merged.update(schema_dict)
    return merged


def _without_metadata_key_filter(
    filters: ImageFilter | None, metadata_key: str
) -> ImageFilter | None:
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


def _apply_image_filters(
    query: QueryType,
    collection_id: UUID,
    filters: ImageFilter | None,
) -> QueryType:
    """Restrict ``query`` to the samples matching ``filters``.

    The filters are applied to an image sample-ids subquery (dimension filters
    reference ``ImageTable``), which the metadata query then joins via ``IN``.
    """
    if filters is None:
        return query
    filtered_sample_ids = (
        select(ImageTable.sample_id)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    filtered_sample_ids = filters.apply(filtered_sample_ids)
    return query.where(col(SampleTable.sample_id).in_(filtered_sample_ids))


def _get_metadata_min_max_count(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
) -> tuple[float, float, int] | None:
    """Aggregate the min, max, and count for a numerical metadata key in SQL.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        metadata_key: The metadata key to aggregate.

    Returns:
        A ``(min, max, count)`` tuple, or ``None`` if the key has no values.
    """
    value_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key, cast_to_float=True
    )
    json_not_null_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key
    ).isnot(None)

    query = (
        select(
            func.min(value_expr),
            func.max(value_expr),
            func.count(value_expr),
        )
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            json_not_null_expr,
        )
    )

    row = session.exec(query).first()
    if row is None or row[0] is None or row[1] is None or row[2] == 0:
        return None
    return float(row[0]), float(row[1]), int(row[2])


def _compute_histogram(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    metadata_key: str,
    stats: tuple[float, float, int],
    filters: ImageFilter | None = None,
    bin_count: int = _HISTOGRAM_BIN_COUNT,
) -> HistogramView:
    """Compute a value-distribution histogram entirely in SQL.

    Bucketing is expressed with dialect-independent SQLAlchemy functions
    (``floor``/``least``/``greatest``) so it works on both DuckDB and
    PostgreSQL without materializing every value in Python. Bin ``i`` covers
    the half-open interval ``[bin_edges[i], bin_edges[i + 1])``; the last bin
    includes its right edge, matching the value at ``max``.

    When all values are equal the range is degenerate, so a single bin holding
    every value is returned.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        metadata_key: The metadata key to bin.
        stats: The ``(min, max, count)`` returned by ``_get_metadata_min_max_count``.
            The min/max always describe the *unfiltered* domain so the bin
            edges stay stable while filters change.
        filters: Optional sample filters restricting which values are counted.
        bin_count: Number of equal-width bins.

    Returns:
        The histogram with bin edges and per-bin counts.
    """
    min_value, max_value, total_count = stats
    if max_value == min_value:
        count = (
            total_count
            if filters is None
            else _count_metadata_values(
                session=session,
                collection_id=collection_id,
                metadata_key=metadata_key,
                filters=filters,
            )
        )
        return HistogramView(bin_edges=[min_value, max_value], counts=[count])

    width = (max_value - min_value) / bin_count

    value_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key, cast_to_float=True
    )
    json_not_null_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key
    ).isnot(None)

    # Bucket index in [0, bin_count - 1]; values equal to max map to the last bin.
    raw_bucket = cast(func.floor((value_expr - min_value) / width), Integer)
    bucket_expr = func.least(func.greatest(raw_bucket, 0), bin_count - 1)

    query = (
        select(bucket_expr.label("bucket"), func.count())
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            json_not_null_expr,
        )
        .group_by(bucket_expr)
    )
    query = _apply_image_filters(query=query, collection_id=collection_id, filters=filters)

    counts_by_bucket = {int(bucket): int(count) for bucket, count in session.exec(query).all()}
    counts = [counts_by_bucket.get(i, 0) for i in range(bin_count)]

    bin_edges = [min_value + (max_value - min_value) * i / bin_count for i in range(bin_count + 1)]
    # Guard against float drift so the last edge is exactly the max value.
    bin_edges[-1] = max_value

    return HistogramView(bin_edges=bin_edges, counts=counts)


def _count_metadata_values(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
    filters: ImageFilter | None,
) -> int:
    """Count non-null values for a metadata key under the given filters."""
    json_not_null_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key
    ).isnot(None)
    query = (
        select(func.count())
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            json_not_null_expr,
        )
    )
    query = _apply_image_filters(query=query, collection_id=collection_id, filters=filters)
    return int(session.exec(query).one())
