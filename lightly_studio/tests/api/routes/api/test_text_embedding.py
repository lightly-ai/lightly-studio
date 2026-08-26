from collections.abc import Mapping
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.embed.manager import (
    EmbedderManager,
    EmbedderManagerProvider,
)
from lightly_studio.embed.random_embedder import RandomEmbedder
from tests import helpers_resolvers


def test_embed_text(db_session: Session, mocker: MockerFixture, test_client: TestClient) -> None:
    # Create a db as the text_embeddings defaults to root_collection
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # Initialize the embedder_manager with a mock variant so it does not update
    # the singleton.
    mocker.patch.object(
        EmbedderManagerProvider,
        "get_embedder_manager",
        return_value=EmbedderManager(),
    )
    # Mock the EmbedderManager return value.
    mocker.patch.object(
        EmbedderManager,
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


def test_embed_text_ignores_embedding_model_id(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    # The new manager holds a single default text embedder, so embedding_model_id
    # is accepted for API compatibility but no longer selects the model.
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(
        EmbedderManagerProvider,
        "get_embedder_manager",
        return_value=EmbedderManager(),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}",
        params={
            "query_text": "sample",
            "embedding_model_id": str(uuid4()),
        },
    )

    # The default RandomEmbedder answers regardless of the model id, producing a
    # vector of its fixed dimension.
    assert response.status_code == HTTP_STATUS_OK
    assert len(response.json()) == RandomEmbedder().load().dimension


def test_embed_text_no_embedder_registered(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(
        EmbedderManagerProvider,
        "get_embedder_manager",
        return_value=EmbedderManager(),
    )
    mocker.patch.object(
        EmbedderManager,
        "embed_text",
        side_effect=ValueError("No text embedder registered."),
    )

    response = test_client.get(
        f"/api/text_embedding/for_collection/{collection_id!s}",
        params={"query_text": "sample"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "No text embedder registered."}
