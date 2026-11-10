"""Transport protocol for collections."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from lightly_studio.models.collection import CollectionCreate, CollectionView, SampleType


class CollectionTransport(Protocol):
    """Creates and finds collections."""

    def create(self, collection: CollectionCreate) -> CollectionView:
        """Create a collection.

        A root collection also gets a new dataset. A child collection uses the dataset
        of its parent.

        Raises:
            ValueError: If a collection with the same name exists under the same parent.
        """

    def get_by_id(self, collection_id: UUID) -> CollectionView | None:
        """Get a collection by ID, or None if it does not exist."""

    def get_by_name(self, name: str, parent_collection_id: UUID | None) -> CollectionView | None:
        """Get a collection by name under a parent, or None if it does not exist.

        Args:
            name: The name of the collection.
            parent_collection_id: The ID of the parent. None finds a root collection.
        """

    def get_or_create_child(
        self, collection_id: UUID, sample_type: SampleType, name: str | None
    ) -> UUID:
        """Get the child collection with a sample type, and create it if it does not exist.

        Args:
            collection_id: The ID of the parent collection.
            sample_type: The sample type of the child collection.
            name: The name of the child collection. None uses a default name.

        Returns:
            The ID of the child collection.
        """
