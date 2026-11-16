from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from tests.helpers_resolvers import create_collection


def test_v1_read_collections(test_client: TestClient, db_session: Session) -> None:
    root = create_collection(session=db_session, collection_name="root")
    create_collection(session=db_session, collection_name="other")
    create_collection(
        session=db_session, collection_name="child", parent_collection_id=root.collection_id
    )

    roots = test_client.get("/api/v1/collections")
    by_name = test_client.get("/api/v1/collections", params={"name": "root"})
    children = test_client.get(
        "/api/v1/collections", params={"parent_collection_id": str(root.collection_id)}
    )

    assert [c["name"] for c in roots.json()] == ["root", "other"]
    assert [c["collection_id"] for c in by_name.json()] == [str(root.collection_id)]
    assert [c["name"] for c in children.json()] == ["child"]


def test_v1_read_collection(test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session, collection_name="root")

    response = test_client.get(f"/api/v1/collections/{collection.collection_id}")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["name"] == "root"


def test_v1_read_collection__not_found(test_client: TestClient) -> None:
    collection_id = UUID("00000000-0000-0000-0000-000000000001")

    response = test_client.get(f"/api/v1/collections/{collection_id}")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
