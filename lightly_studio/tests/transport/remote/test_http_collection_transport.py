from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.transport.collection_transport import CollectionTransport
from lightly_studio.transport.remote.http_collection_transport import HttpCollectionTransport
from tests.helpers_resolvers import create_collection


class TestHttpCollectionTransport:
    def test_create(self, test_client: TestClient) -> None:
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.create(collection=CollectionCreate(name="a", sample_type=SampleType.IMAGE))

    def test_get_by_id(self, test_client: TestClient, db_session: Session) -> None:
        collection = create_collection(session=db_session, collection_name="root")
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)
        missing_id = UUID("00000000-0000-0000-0000-000000000001")

        found = transport.get_by_id(collection_id=collection.collection_id)

        assert found is not None
        assert found.name == "root"
        assert transport.get_by_id(collection_id=missing_id) is None

    def test_get_by_name(self, test_client: TestClient, db_session: Session) -> None:
        collection = create_collection(session=db_session, collection_name="root")
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)

        found = transport.get_by_name(name="root", parent_collection_id=None)

        assert found is not None
        assert found.collection_id == collection.collection_id
        assert transport.get_by_name(name="other", parent_collection_id=None) is None

    def test_get_all_by_parent(self, test_client: TestClient, db_session: Session) -> None:
        root = create_collection(session=db_session, collection_name="root")
        create_collection(
            session=db_session, collection_name="child", parent_collection_id=root.collection_id
        )
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)

        children = transport.get_all_by_parent(parent_collection_id=root.collection_id, name=None)

        assert [c.name for c in children] == ["child"]

    def test_create_group_components(self, test_client: TestClient) -> None:
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.create_group_components(
                parent_collection_id=UUID("00000000-0000-0000-0000-000000000001"),
                components=[("front", SampleType.IMAGE)],
            )

    def test_get_group_components(self, test_client: TestClient) -> None:
        transport: CollectionTransport = HttpCollectionTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.get_group_components(
                parent_collection_id=UUID("00000000-0000-0000-0000-000000000001")
            )
