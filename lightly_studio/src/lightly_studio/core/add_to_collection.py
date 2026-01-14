"""TODO."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType


@runtime_checkable
class AddToCollection(Protocol):
    """Protocol for adding samples to a collection."""

    def add_to_collection(self, session: Session, collection_id: UUID) -> UUID:
        """Add a sample defined by self to a collection.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to add the sample to.

        Returns:
            The UUID of the created sample in the collection.
        """
        ...

    def sample_type(self) -> SampleType:
        """Return the sample type."""
        ...
