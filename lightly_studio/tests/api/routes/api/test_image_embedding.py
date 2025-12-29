from typing import Generator

import pytest
import requests
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_OK,
)
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from tests import helpers_resolvers


@pytest.fixture
def mock_embedding_manager(mocker: MockerFixture) -> Generator[EmbeddingManager, None, None]:
    """Mock the EmbeddingManagerProvider to return a mock EmbeddingManager."""
    manager = mocker.create_autospec(EmbeddingManager, instance=True)
    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=manager,
    )
    return manager


def test_embed_image_from_file(
    db_session: Session,
    mock_embedding_manager: EmbeddingManager,
    test_client: TestClient,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # Mock the compute_image_embedding return value.
    mock_embedding_manager.compute_image_embedding.return_value = [[0.1, 0.2, 0.3]]

    # Prepare file upload
    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    response = test_client.post(
        f"/api/image_embedding/from_file/for_collection/{collection_id!s}",
        files=files,
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [0.1, 0.2, 0.3]
    mock_embedding_manager.compute_image_embedding.assert_called_once()


def test_embed_image_from_file_error(
    db_session: Session,
    mock_embedding_manager: EmbeddingManager,
    test_client: TestClient,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    mock_embedding_manager.compute_image_embedding.side_effect = ValueError("Embedding failed")

    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    response = test_client.post(
        f"/api/image_embedding/from_file/for_collection/{collection_id!s}",
        files=files,
    )

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR
    assert "Embedding failed" in response.json()["detail"]


def test_embed_image_from_url(
    db_session: Session,
    mock_embedding_manager: EmbeddingManager,
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # Mock compute_image_embedding
    mock_embedding_manager.compute_image_embedding.return_value = [[0.4, 0.5, 0.6]]

    # Mock requests.get
    mock_response = mocker.Mock()
    mock_response.raw = mocker.Mock()
    mock_response.raw.read.return_value = b""  # Empty read for shutil.copyfileobj
    mock_response.raise_for_status.return_value = None
    mocker.patch(
        "lightly_studio.api.routes.api.image_embedding.requests.get",
        return_value=mock_response,
    )

    response = test_client.post(
        f"/api/image_embedding/from_url/for_collection/{collection_id!s}",
        params={"url": "http://example.com/image.jpg"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [0.4, 0.5, 0.6]
    mock_embedding_manager.compute_image_embedding.assert_called_once()


def test_embed_image_from_url_download_error(
    db_session: Session,
    mock_embedding_manager: EmbeddingManager,
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    # Mock requests.get to fail with RequestException
    mocker.patch(
        "lightly_studio.api.routes.api.image_embedding.requests.get",
        side_effect=requests.RequestException("Download failed"),
    )

    response = test_client.post(
        f"/api/image_embedding/from_url/for_collection/{collection_id!s}",
        params={"url": "http://example.com/image.jpg"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "Download failed" in response.json()["detail"]
