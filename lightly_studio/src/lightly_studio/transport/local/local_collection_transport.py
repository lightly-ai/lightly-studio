"""Collection transport that calls the resolvers in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionWithoutChildrenView,
    GroupComponentDefinition,
    SampleType,
)
from lightly_studio.resolvers import collection_resolver


class LocalCollectionTransport:
    """Implements `CollectionTransport` with the persistent database session."""

    def create(self, collection: CollectionCreate) -> CollectionWithoutChildrenView:
        """Create a collection."""
        created = collection_resolver.create(
            session=db_manager.persistent_session(), collection=collection
        )
        return CollectionWithoutChildrenView.model_validate(created)

    def get_by_id(self, collection_id: UUID) -> CollectionWithoutChildrenView | None:
        """Get a collection by ID, or None if it does not exist."""
        collection = collection_resolver.get_by_id(
            session=db_manager.persistent_session(), collection_id=collection_id
        )
        return (
            None if collection is None else CollectionWithoutChildrenView.model_validate(collection)
        )

    def get_by_name(
        self, name: str, parent_collection_id: UUID | None
    ) -> CollectionWithoutChildrenView | None:
        """Get a collection by name under a parent, or None if it does not exist."""
        collections = self.get_all_by_parent(parent_collection_id=parent_collection_id, name=name)
        return collections[0] if collections else None

    def get_all_by_parent(
        self, parent_collection_id: UUID | None, name: str | None
    ) -> list[CollectionWithoutChildrenView]:
        """Get the child collections of a parent, sorted by creation time."""
        collections = collection_resolver.get_all_by_parent(
            session=db_manager.persistent_session(),
            parent_collection_id=parent_collection_id,
            name=name,
        )
        return [
            CollectionWithoutChildrenView.model_validate(collection) for collection in collections
        ]

    def get_or_create_child(
        self, collection_id: UUID, sample_type: SampleType, name: str | None
    ) -> UUID:
        """Get the child collection with a sample type, and create it if it does not exist."""
        return collection_resolver.get_or_create_child_collection(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            sample_type=sample_type,
            name=name,
        )

    def create_group_components(
        self, parent_collection_id: UUID, components: Sequence[GroupComponentDefinition]
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Create the component collections of a group collection."""
        created = collection_resolver.create_group_components(
            session=db_manager.persistent_session(),
            parent_collection_id=parent_collection_id,
            components=components,
        )
        return {
            name: CollectionWithoutChildrenView.model_validate(collection)
            for name, collection in created.items()
        }

    def get_group_components(
        self, parent_collection_id: UUID
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Get the component collections of a group collection by component name."""
        components = collection_resolver.get_group_components(
            session=db_manager.persistent_session(), parent_collection_id=parent_collection_id
        )
        return {
            name: CollectionWithoutChildrenView.model_validate(collection)
            for name, collection in components.items()
        }
