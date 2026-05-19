"""Resolver for retrieving metadata values for a single key."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio import db_json
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
    schema_type_expr = db_json.json_extract(
        column=SampleMetadataTable.metadata_schema,
        field=key,
    )

    rows = session.exec(
        select(SampleMetadataTable)
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
    for row in rows:
        row_metadata_type = row.metadata_schema[key]
        if metadata_type is None:
            metadata_type = row_metadata_type
        elif metadata_type != row_metadata_type:
            raise ValueError(
                f"Metadata field '{key}': value does not match schema type {metadata_type!r}."
            )
        value = row.data.get(key)
        if value is not None:
            sample_to_value[row.sample_id] = value

    return sample_to_value, metadata_type
