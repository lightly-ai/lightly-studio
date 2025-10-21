"""Resolver for operations for retrieving metadata."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from .get_by_sample_id import get_by_sample_id


def get_value_for_sample(session: Session, sample_id: UUID, key: str) -> Any | None:
    """Get a specific metadata value for a sample.

    Args:
        session: The database session.
        sample_id: The sample's UUID.
        key: The metadata key.

    Returns:
        The value for the given key, or None if not found.
    """
    metadata = get_by_sample_id(session=session, sample_id=sample_id)
    if metadata is None:
        return None
    return metadata.data.get(key)
