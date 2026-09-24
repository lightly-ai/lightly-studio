from collections.abc import Mapping
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_OK,
)
from lightly_studio.embed import embed_samples
from lightly_studio.embed.errors import (
    MissingCapabilityError,
    NoDefaultEmbeddingModelError,
    RemoteEmbedderUnavailableError,
)
from tests import helpers_resolvers


def test_embed_text(db_session: Session, mocker: MockerFixture, test_client: TestClient) -> None:
    # Create a db as the text_embeddings defaults to root_collection
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(
        embed_samples,
        "embed_text_for_collection",
        return_value=[0.1, 0.2, 0.3],
    )

    # Make the request to the `/text_embedding` endpoint.
    params: Mapping[str, str] = {
        "query_text": "sample",
    }
    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}", params=params
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [0.1, 0.2, 0.3]


def test_embed_text__model_override_not_supported(test_client: TestClient) -> None:
    # A per-request embedding model override is not supported: passing an
    # embedding_model_id must raise instead of silently using the collection default.
    with pytest.raises(NotImplementedError, match="model override is not supported"):
        test_client.get(
            f"/api/text_embedding/for_collection/{uuid4()!s}",
            params={
                "query_text": "sample",
                "embedding_model_id": str(uuid4()),
            },
        )


def test_embed_text__missing_capability(
    db_session: Session, mocker: MockerFixture, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    mocker.patch.object(
        embed_samples,
        "embed_text_for_collection",
        side_effect=MissingCapabilityError(space_key="my-space"),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}", params={"query_text": "sample"}
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert (
        response.json()["detail"]
        == "The embedding space 'my-space' of this collection cannot embed text."
    )


def test_embed_text__no_default_model(
    db_session: Session, mocker: MockerFixture, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    mocker.patch.object(
        embed_samples,
        "embed_text_for_collection",
        side_effect=NoDefaultEmbeddingModelError("The collection has no default embedding model."),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}", params={"query_text": "sample"}
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert response.json()["detail"] == "The collection has no default embedding model."


def test_embed_text__remote_unavailable(
    db_session: Session, mocker: MockerFixture, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    mocker.patch.object(
        embed_samples,
        "embed_text_for_collection",
        side_effect=RemoteEmbedderUnavailableError(
            space_key="my-space", url="http://embedder.test"
        ),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}", params={"query_text": "sample"}
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json()["detail"] == (
        "The embedding server at 'http://embedder.test' for the embedding space 'my-space' "
        "cannot be used."
    )


def test_embed_text__value_error(
    db_session: Session, mocker: MockerFixture, test_client: TestClient
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    mocker.patch.object(
        embed_samples,
        "embed_text_for_collection",
        side_effect=ValueError("Embedding failed"),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}", params={"query_text": "sample"}
    )

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Embedding failed"
