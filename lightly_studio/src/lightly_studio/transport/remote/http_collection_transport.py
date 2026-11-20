"""Collection transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionWithoutChildrenView,
    GroupComponentDefinition,
    SampleType,
)
from lightly_studio.transport.remote import http_requests


class HttpCollectionTransport:
    """Implements `CollectionTransport` over HTTP. Writes are not supported yet."""

    def __init__(self, client: httpx.Client) -> None:
        """Create the transport with an HTTP client for the Studio backend."""
        self._client = client

    def create(self, collection: CollectionCreate) -> CollectionWithoutChildrenView:
        """Create a collection. Not supported over HTTP yet."""
        raise NotImplementedError("Creating a collection over HTTP is not supported yet.")

    def get_by_id(self, collection_id: UUID) -> CollectionWithoutChildrenView | None:
        """Get a collection by ID, or None if it does not exist."""
        body = http_requests.get(client=self._client, path=f"/collections/{collection_id}")
        return None if body is None else CollectionWithoutChildrenView.model_validate(body)

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
        params = {"parent_collection_id": parent_collection_id, "name": name}
        body = http_requests.get(client=self._client, path="/collections", params=params)
        return [CollectionWithoutChildrenView.model_validate(item) for item in body]

    def get_or_create_child(
        self, collection_id: UUID, sample_type: SampleType, name: str | None
    ) -> UUID:
        """Get or create a child collection. Not supported over HTTP yet."""
        raise NotImplementedError("Creating a collection over HTTP is not supported yet.")

    def create_group_components(
        self, parent_collection_id: UUID, components: Sequence[GroupComponentDefinition]
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Create group components. Not supported over HTTP yet."""
        raise NotImplementedError("Creating group components over HTTP is not supported yet.")

    def get_group_components(
        self, parent_collection_id: UUID
    ) -> dict[str, CollectionWithoutChildrenView]:
        """Get group components. Not supported over HTTP yet."""
        raise NotImplementedError("Getting group components over HTTP is not supported yet.")
