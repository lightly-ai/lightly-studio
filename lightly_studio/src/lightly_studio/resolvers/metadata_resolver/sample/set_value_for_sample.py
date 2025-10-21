"""Resolver for operations for setting metadata."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.metadata import (
    SampleMetadataTable,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_by_sample_id import (
    get_by_sample_id,
)


def set_value_for_sample(
    session: Session,
    sample_id: UUID,
    key: str,
    value: Any,
) -> SampleMetadataTable:
    """Set a specific metadata value for a sample.

    Args:
        session: The database session.
        sample_id: The sample's UUID.
        key: The metadata key.
        value: The value to set.

    Returns:
        The updated CustomMetadataTable instance.

    Raises:
        ValueError: If the value type doesn't match the schema.
    """
    metadata = get_by_sample_id(session=session, sample_id=sample_id)
    if metadata is None:
        # Create new metadata row if it does not exist
        metadata = SampleMetadataTable(
            sample_id=sample_id,
            data={},
            metadata_schema={},
        )
        session.add(metadata)

    metadata.set_value(key, value)

    # Commit changes and refresh the object
    session.commit()
    session.refresh(metadata)
    return metadata
