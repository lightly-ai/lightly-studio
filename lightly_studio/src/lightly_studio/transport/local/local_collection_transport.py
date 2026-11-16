"""Collection transport that calls the resolvers in the same process."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionWithoutChildrenView,
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
        collection = collection_resolver.get_table_by_name(
            session=db_manager.persistent_session(),
            name=name,
            parent_collection_id=parent_collection_id,
        )
        return (
            None if collection is None else CollectionWithoutChildrenView.model_validate(collection)
        )

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
