from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from tests.helpers_resolvers import create_collection


def test_v1_read_collections(test_client: TestClient, db_session: Session) -> None:
    newer = create_collection(session=db_session, collection_name="newer")
    older = create_collection(session=db_session, collection_name="older")
    newer.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    create_collection(
        session=db_session, collection_name="child", parent_collection_id=older.collection_id
    )

    response = test_client.get("/api/v1/collections")

    assert [c["name"] for c in response.json()] == ["older", "newer"]


def test_v1_read_collections__by_name(test_client: TestClient, db_session: Session) -> None:
    root = create_collection(session=db_session, collection_name="root")
    create_collection(session=db_session, collection_name="other")

    response = test_client.get("/api/v1/collections", params={"name": "root"})

    assert [c["collection_id"] for c in response.json()] == [str(root.collection_id)]


def test_v1_read_collections__by_parent(test_client: TestClient, db_session: Session) -> None:
    root = create_collection(session=db_session, collection_name="root")
    create_collection(
        session=db_session, collection_name="child", parent_collection_id=root.collection_id
    )

    response = test_client.get(
        "/api/v1/collections", params={"parent_collection_id": str(root.collection_id)}
    )

    assert [c["name"] for c in response.json()] == ["child"]


def test_v1_read_collection(test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session, collection_name="root")

    response = test_client.get(f"/api/v1/collections/{collection.collection_id}")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["name"] == "root"


def test_v1_read_collection__not_found(test_client: TestClient) -> None:
    collection_id = UUID("00000000-0000-0000-0000-000000000001")

    response = test_client.get(f"/api/v1/collections/{collection_id}")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
