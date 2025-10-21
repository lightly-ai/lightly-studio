"""Resolver for operations for setting metadata."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.metadata import SampleMetadataTable


def bulk_update_metadata(
    session: Session,
    sample_metadata: list[tuple[UUID, dict[str, Any]]],
) -> None:
    """Bulk insert or update metadata for multiple samples.

    If a sample does not have metadata, a new metadata row is created.
    If a sample already has metadata, the new key-value pairs are merged with the existing metadata.

    Args:
        session: The database session.
        sample_metadata: List of (sample_id, metadata_dict) tuples.
    """
    # TODO(Mihnea, 10/2025): Consider using SQLAlchemy's bulk operations
    #  (Session.bulk_insert/update_mappings) if performance becomes a bottleneck.
    if not sample_metadata:
        return

    # Get all existing metadata rows for the given sample IDs.
    sample_ids = [s[0] for s in sample_metadata]
    existing_metadata = session.exec(
        select(SampleMetadataTable).where(col(SampleMetadataTable.sample_id).in_(sample_ids))
    ).all()
    sample_id_to_existing_metadata = {meta.sample_id: meta for meta in existing_metadata}

    for sample_id, new_metadata in sample_metadata:
        metadata = sample_id_to_existing_metadata.get(
            sample_id, SampleMetadataTable(sample_id=sample_id)
        )
        for key, value in new_metadata.items():
            metadata.set_value(key, value)
        session.add(metadata)

    session.commit()
