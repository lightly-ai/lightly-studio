"""Resolver for operations for retrieving metadata info."""

from __future__ import annotations

from uuid import UUID

import numpy as np
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
            values = _get_metadata_numeric_values(
                session=session, collection_id=collection_id, metadata_key=key
            )
            if values:
                cast = int if metadata_type == "integer" else float
                metadata_info.min = cast(min(values))
                metadata_info.max = cast(max(values))
                metadata_info.histogram = _compute_histogram(values=values)

        result.append(metadata_info)

    return result


def _get_metadata_numeric_values(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
) -> list[float]:
    """Fetch all non-null values for a specific numerical metadata key.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        metadata_key: The metadata key to fetch values for.

    Returns:
        List of the numeric values (as floats) for the given key.
    """
    json_value_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key, cast_to_float=True
    )
    json_not_null_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key
    ).isnot(None)

    query = (
        select(json_value_expr)
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

    return [float(value) for value in session.exec(query).all() if value is not None]


def _compute_histogram(values: list[float]) -> HistogramView:
    """Compute a value-distribution histogram in Python.

    Binning is done with numpy so it is independent of the database backend
    (no ``width_bucket()`` or dialect-specific SQL). When all values are equal,
    numpy produces a single degenerate range which we keep as-is.

    Args:
        values: The numeric values to bin. Must be non-empty.

    Returns:
        The histogram with bin edges and per-bin counts.
    """
    assert values
    counts, bin_edges = np.histogram(values, bins=_HISTOGRAM_BIN_COUNT)
    return HistogramView(
        bin_edges=[float(edge) for edge in bin_edges],
        counts=[int(count) for count in counts],
    )
