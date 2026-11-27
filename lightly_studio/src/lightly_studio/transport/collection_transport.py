"""Transport protocol for collections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionWithoutChildrenView,
    GroupComponentDefinition,
    SampleType,
)


class CollectionTransport(Protocol):
    """Creates and finds collections."""

    def create(self, collection: CollectionCreate) -> CollectionWithoutChildrenView:
        """Create a collection.

        A root collection also gets a new dataset. A child collection uses the dataset
        of its parent.

        Raises:
            ValueError: If a collection with the same name exists under the same parent.
        """

    def get_by_id(self, collection_id: UUID) -> CollectionWithoutChildrenView | None:
        """Get a collection by ID, or None if it does not exist."""

    def get_by_name(
        self, name: str, parent_collection_id: UUID | None
    ) -> CollectionWithoutChildrenView | None:
        """Get a collection by name under a parent, or None if it does not exist.

        Args:
            name: The name of the collection.
            parent_collection_id: The ID of the parent. None finds a root collection.
        """

    def get_all_by_parent(
        self, parent_collection_id: UUID | None, name: str | None
    ) -> list[CollectionWithoutChildrenView]:
        """Get the child collections of a parent, sorted by creation time.

        Args:
            parent_collection_id: The ID of the parent. None gets the root collections.
            name: The name of the collections to get. None gets all names.
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

    def create_group_components(
        self, parent_collection_id: UUID, components: Sequence[GroupComponentDefinition]
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Create the component collections of a group collection.

        Args:
            parent_collection_id: The ID of the group collection.
            components: The name and the sample type of each component, in order.

        Returns:
            The component collections by component name.

        Raises:
            ValueError: If the parent is not a group collection, if it has components, or if
                two components have the same name.
        """

    def get_group_components(
        self, parent_collection_id: UUID
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Get the component collections of a group collection by component name.

        Raises:
            ValueError: If the parent does not exist or is not a group collection.
        """
