"""Protocol for creating samples in a collection."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType


@runtime_checkable
class CreateSample(Protocol):
    """Protocol for creating samples in a collection."""

    def create_in_collection(self, session: Session, collection_id: UUID) -> UUID:
        """Create a sample defined by self in a collection.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to create the sample in.

        Returns:
            The UUID of the created sample.
        """
        ...

    def sample_type(self) -> SampleType:
        """Return the sample type."""
        ...
