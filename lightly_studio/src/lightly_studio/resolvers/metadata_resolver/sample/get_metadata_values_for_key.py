"""Resolver for retrieving metadata values for a single key."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable


def get_metadata_values_for_key(
    session: Session,
    collection_id: UUID,
    key: str,
) -> tuple[dict[UUID, Any], str | None]:
    """Get metadata values and schema type for one key in a collection.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        key: The metadata key to retrieve.

    Returns:
        A tuple containing:
            - A mapping from sample ID to the metadata value for `key`.
              Only samples that have a non-null value for `key` are included.
            - The schema type for `key`, or `None` if the key is not present in
              the collection schema.
    """
    schema_type_expr = db_json.json_extract_string(
        column=SampleMetadataTable.metadata_schema,
        field=key,
    )
    value_expr = db_json.json_extract_string(column=SampleMetadataTable.data, field=key)

    rows = session.exec(
        select(SampleMetadataTable.sample_id, value_expr, schema_type_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            schema_type_expr.isnot(None),
        )
    ).all()
    if not rows:
        return {}, None

    sample_to_value: dict[UUID, Any] = {}
    metadata_type: str | None = None
    for sample_id, value, row_metadata_type in rows:
        if metadata_type is None:
            metadata_type = row_metadata_type
        elif metadata_type != row_metadata_type:
            raise ValueError(
                f"Metadata field '{key}': value does not match schema type {metadata_type!r}."
            )
        if value is not None:
            sample_to_value[sample_id] = _parse_value(value=value, metadata_type=row_metadata_type)

    return sample_to_value, metadata_type


def _parse_value(value: str, metadata_type: str) -> Any:
    """Parse a scalar JSON extraction result according to its stored schema."""
    if metadata_type == "string":
        return value
    if metadata_type == "boolean":
        return value.lower() == "true"
    if metadata_type == "integer":
        return int(value)
    if metadata_type == "float":
        return float(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
