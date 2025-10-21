"""Resolver for operations for retrieving metadata."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.metadata import SampleMetadataTable


def get_by_sample_id(session: Session, sample_id: UUID) -> SampleMetadataTable | None:
    """Retrieve the metadata object for a given sample.

    Args:
        session: The database session.
        sample_id: The sample's UUID.

    Returns:
        The CustomMetadataTable instance or None if not found.
    """
    return session.exec(
        select(SampleMetadataTable).where(SampleMetadataTable.sample_id == sample_id)
    ).one_or_none()
