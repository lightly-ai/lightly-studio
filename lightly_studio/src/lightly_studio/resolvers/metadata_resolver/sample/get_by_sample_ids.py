"""Resolver for operations for retrieving metadata."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.metadata import SampleMetadataTable


def get_by_sample_ids(session: Session, sample_ids: Sequence[UUID]) -> list[SampleMetadataTable]:
    """Get the metadata rows of samples. A sample without metadata has no row in the result."""
    if not sample_ids:
        return []
    return list(
        session.exec(
            select(SampleMetadataTable).where(
                db_array.in_array(column=col(SampleMetadataTable.sample_id), values=sample_ids)
            )
        ).all()
    )
