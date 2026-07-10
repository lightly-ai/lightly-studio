"""Resolver for operations for retrieving metadata info."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.metadata import (
    MetadataInfoView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable

# Metadata types treated as categorical, i.e. exposed via distinct ``values``.
CATEGORICAL_METADATA_TYPES = ("string", "boolean")


def get_all_metadata_keys_and_schema(
    session: Session,
    collection_id: UUID,
) -> list[MetadataInfoView]:
    """Get all unique metadata keys and their schema for a collection.

    Args:
        session: The database session.
        collection_id: The collection's UUID.

    Returns:
        List of dicts with 'name', 'type', and optionally 'min'/'max' for numerical types.
    """
    # Query all metadata_schema dicts for samples in the collection
    rows = session.exec(
        select(SampleMetadataTable.metadata_schema)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    # Merge all schemas
    merged: dict[str, str] = {}
    for schema_dict in rows:
        merged.update(schema_dict)

    # Get min and max values for numerical metadata
    result = []
    for key, metadata_type in merged.items():
        metadata_info = MetadataInfoView(name=key, type=metadata_type)

        # Add min and max for numerical types
        if metadata_type in ["integer", "float"]:
            min_max_values = _get_metadata_min_max_values(
                session, collection_id, key, metadata_type
            )
            if min_max_values:
                metadata_info.min = min_max_values[0]
                metadata_info.max = min_max_values[1]

        # Add distinct values for categorical types so the frontend can list
        # them without deriving them from a coloring hue wheel.
        if metadata_type in CATEGORICAL_METADATA_TYPES:
            metadata_info.values = _get_metadata_distinct_values(session, collection_id, key)

        result.append(metadata_info)

    return result


def _get_metadata_distinct_values(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
) -> list[str]:
    """Get the sorted distinct display values for a categorical metadata key.

    Uses a SQL ``DISTINCT`` on the JSON-extracted value so only the (small)
    set of distinct values is materialized rather than every row. Booleans are
    rendered as ``"true"``/``"false"`` to match the frontend's categorical
    display convention.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        metadata_key: The categorical metadata key to collect values for.

    Returns:
        A sorted list of distinct display values.
    """
    value_expr = db_json.json_extract(column=SampleMetadataTable.data, field=metadata_key)
    rows = session.exec(
        select(value_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            value_expr.isnot(None),
        )
        .distinct()
    ).all()
    return sorted({format_categorical_value(_decode_json_extracted(row)) for row in rows})


def _decode_json_extracted(raw: Any) -> Any:
    """Decode a value returned by ``json_extract`` into a Python value.

    DuckDB's ``json_extract`` returns JSON-encoded text (e.g. ``'"city"'``,
    ``'true'``) while PostgreSQL's ``->>`` returns plain text (``'city'``). This
    normalizes both by attempting a JSON decode and falling back to the raw
    value (covering PostgreSQL plain strings and already-decoded values).
    """
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def format_categorical_value(value: object) -> str:
    """Format a categorical metadata value as a display string.

    Args:
        value: The raw metadata value (string or boolean).

    Returns:
        ``"true"``/``"false"`` for booleans, ``str(value)`` otherwise.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _get_metadata_min_max_values(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
    metadata_type: str,
) -> tuple[int, int] | tuple[float, float] | None:
    """Get min and max values for a specific numerical metadata key.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        metadata_key: The metadata key to get min/max for.
        metadata_type: The metadata type ("integer" or "float").

    Returns:
        Tuple with 'min' and 'max' values, or None if no values found.
    """
    json_value_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key, cast_to_float=True
    )
    json_not_null_expr = db_json.json_extract(
        column=SampleMetadataTable.data, field=metadata_key
    ).isnot(None)

    query = (
        select(
            func.min(json_value_expr),
            func.max(json_value_expr),
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

    result = session.exec(query).first()

    if result and result[0] is not None and result[1] is not None:
        # Convert to appropriate type
        if metadata_type == "integer":
            return int(result[0]), int(result[1])
        if metadata_type == "float":
            return float(result[0]), float(result[1])

    return None
