from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import embedding_model_service_resolver
from tests import helpers_resolvers


def test_read_embedding_model(db_session: Session, test_client: TestClient) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="customer-model",
        embedding_model_hash="customer-model-v1",
    )

    response = test_client.get(f"/api/collections/{collection_id}/embedding_model")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "embedding_model_id": str(embedding_model.embedding_model_id),
        "name": "customer-model",
        "embedding_model_hash": "customer-model-v1",
        "embedding_dimension": 128,
        "serving_url": None,
    }


def test_read_embedding_model__with_serving_url(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_hash="customer-model-v1",
    )
    embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://embeddings.corp.example",
    )

    response = test_client.get(f"/api/collections/{collection_id}/embedding_model")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["serving_url"] == "https://embeddings.corp.example"


def test_read_embedding_model__no_model(db_session: Session, test_client: TestClient) -> None:
    """A collection without embeddings reports no model rather than erroring."""
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    response = test_client.get(f"/api/collections/{collection_id}/embedding_model")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is None


def test_read_embedding_model__unknown_collection(test_client: TestClient) -> None:
    response = test_client.get(f"/api/collections/{uuid4()}/embedding_model")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_update_embedding_model_serving_url(db_session: Session, test_client: TestClient) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_hash="customer-model-v1",
    )

    response = test_client.put(
        "/api/embedding_models/customer-model-v1/serving_url",
        json={"serving_url": "https://embeddings.corp.example"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["serving_url"] == "https://embeddings.corp.example"
    stored = embedding_model_service_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="customer-model-v1"
    )
    assert stored is not None
    assert stored.serving_url == "https://embeddings.corp.example"


def test_update_embedding_model_serving_url__clears(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_hash="customer-model-v1",
    )
    embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://embeddings.corp.example",
    )

    response = test_client.put(
        "/api/embedding_models/customer-model-v1/serving_url",
        json={"serving_url": None},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["serving_url"] is None
    assert (
        embedding_model_service_resolver.get_by_model_hash(
            session=db_session, embedding_model_hash="customer-model-v1"
        )
        is None
    )


def test_update_embedding_model_serving_url__rejects_insecure_url(
    db_session: Session, test_client: TestClient
) -> None:
    """Mixed content is caught here rather than as an opaque failure during a search."""
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_hash="customer-model-v1",
    )

    response = test_client.put(
        "/api/embedding_models/customer-model-v1/serving_url",
        json={"serving_url": "http://192.168.1.20:8123"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_update_embedding_model_serving_url__unknown_model(test_client: TestClient) -> None:
    """Refuse to store a URL for a model no collection was embedded with."""
    response = test_client.put(
        "/api/embedding_models/never-indexed/serving_url",
        json={"serving_url": "https://embeddings.corp.example"},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
