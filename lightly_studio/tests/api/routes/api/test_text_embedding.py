from collections.abc import Mapping
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from tests import helpers_resolvers


def test_embed_text(db_session: Session, mocker: MockerFixture, test_client: TestClient) -> None:
    # Create a db as the text_embeddings defaults to root_collection
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # Initialize the embedding_manager with a mock variant so it does not update
    # the singleton.
    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )
    # Mock the EmbeddingManager return value.
    mocker.patch.object(
        EmbeddingManager,
        "embed_text",
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


def test_embed_text__loads_default_model_after_restart(
    db_session: Session, mocker: MockerFixture, test_client: TestClient
) -> None:
    """A fresh EmbeddingManager (e.g. after a server restart) loads the default model lazily."""
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # A fresh manager whose in-memory model registry is empty, as after a restart.
    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )
    mocker.patch(
        "lightly_studio.dataset.embedding_manager._load_embedding_generator_from_env",
        return_value=RandomEmbeddingGenerator(dimension=3),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}",
        params={"query_text": "sample"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert len(response.json()) == 3


def test_embed_text_embedding_invalid_model_id(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    # Make the request to the `/samples` endpoint
    # Create a db as the text_embeddings defaults to root_collection
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )
    test_uuid = uuid4()

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}",
        params={
            "query_text": "sample",
            "embedding_model_id": str(test_uuid),
        },
    )
    assert response.status_code == 500
    assert response.json() == {"detail": f"No embedding model found with ID {test_uuid}"}
