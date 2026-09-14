from collections.abc import Mapping
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
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
