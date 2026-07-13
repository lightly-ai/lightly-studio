"""Resolver for operations for retrieving metadata info."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Integer, cast, func
from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.metadata import (
    HistogramView,
    MetadataInfoView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable

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
    # Query all metadata_schema dicts for samples in the collection.
    rows = session.exec(
        select(SampleMetadataTable.metadata_schema)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    # Merge all schemas.
    merged: dict[str, str] = {}
    for schema_dict in rows:
        merged.update(schema_dict)

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


def _compute_histogram(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
    stats: tuple[float, float, int],
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

    Returns:
        The histogram with bin edges and per-bin counts.
    """
    min_value, max_value, total_count = stats
    if max_value == min_value:
        return HistogramView(bin_edges=[min_value, max_value], counts=[total_count])

    bin_count = _HISTOGRAM_BIN_COUNT
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

    counts_by_bucket = {int(bucket): int(count) for bucket, count in session.exec(query).all()}
    counts = [counts_by_bucket.get(i, 0) for i in range(bin_count)]

    bin_edges = [min_value + (max_value - min_value) * i / bin_count for i in range(bin_count + 1)]
    # Guard against float drift so the last edge is exactly the max value.
    bin_edges[-1] = max_value

    return HistogramView(bin_edges=bin_edges, counts=counts)
