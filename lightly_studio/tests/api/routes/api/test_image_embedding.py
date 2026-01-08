from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_OK,
)
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from tests import helpers_resolvers


def test_embed_image_from_file(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
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
        "compute_image_embedding",
        return_value=[0.1, 0.2, 0.3],
    )

    # Prepare file upload
    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    response = test_client.post(
        f"/api/image_embedding/from_file/for_collection/{collection_id!s}",
        files=files,
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [0.1, 0.2, 0.3]


def test_embed_image_from_file_error(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )
    mocker.patch.object(
        EmbeddingManager,
        "compute_image_embedding",
        side_effect=ValueError("Embedding failed"),
    )

    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    response = test_client.post(
        f"/api/image_embedding/from_file/for_collection/{collection_id!s}",
        files=files,
    )

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR
    assert "Embedding failed" in response.json()["detail"]
