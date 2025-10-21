"""Resolver for operations for retrieving metadata info."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, func
from sqlmodel import Session, col, select

from lightly_studio.models.metadata import (
    MetadataInfoView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable


def get_all_metadata_keys_and_schema(
    session: Session,
    dataset_id: UUID,
) -> list[MetadataInfoView]:
    """Get all unique metadata keys and their schema for a dataset.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.

    Returns:
        List of dicts with 'name', 'type', and optionally 'min'/'max' for numerical types.
    """
    # Query all metadata_schema dicts for samples in the dataset
    rows = session.exec(
        select(SampleMetadataTable.metadata_schema)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.dataset_id == dataset_id)
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
            min_max_values = _get_metadata_min_max_values(session, dataset_id, key, metadata_type)
            if min_max_values:
                metadata_info.min = min_max_values[0]
                metadata_info.max = min_max_values[1]

        result.append(metadata_info)

    return result


def _get_metadata_min_max_values(
    session: Session,
    dataset_id: UUID,
    metadata_key: str,
    metadata_type: str,
) -> tuple[int, int] | tuple[float, float] | None:
    """Get min and max values for a specific numerical metadata key.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.
        metadata_key: The metadata key to get min/max for.
        metadata_type: The metadata type ("integer" or "float").

    Returns:
        Tuple with 'min' and 'max' values, or None if no values found.
    """
    # Build JSON path for the metadata key.
    json_path = f"$.{metadata_key}"

    query = (
        select(
            func.min(func.cast(func.json_extract(SampleMetadataTable.data, json_path), Float)),
            func.max(func.cast(func.json_extract(SampleMetadataTable.data, json_path), Float)),
        )
        .select_from(SampleTable)
        .join(SampleMetadataTable, col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id))
        .where(
            SampleTable.dataset_id == dataset_id,
            func.json_extract(SampleMetadataTable.data, json_path).is_not(None),
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
