from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_OK,
)
from lightly_studio.embed import embed_samples
from tests import helpers_resolvers


def test_embed_image_from_file(
    db_session: Session,
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    mocker.patch.object(embed_samples, "embed_image_for_collection", return_value=[0.1, 0.2, 0.3])

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
        embed_samples,
        "embed_image_for_collection",
        side_effect=ValueError("Embedding failed"),
    )

    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    response = test_client.post(
        f"/api/image_embedding/from_file/for_collection/{collection_id!s}",
        files=files,
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "Embedding failed" in response.json()["detail"]


def test_embed_image_from_file__model_override_not_supported(test_client: TestClient) -> None:
    # A per-request embedding model override is not supported: passing an
    # embedding_model_id must raise instead of silently using the collection default.
    files = {"file": ("test_image.jpg", b"fake image content", "image/jpeg")}

    with pytest.raises(NotImplementedError, match="model override is not supported"):
        test_client.post(
            f"/api/image_embedding/from_file/for_collection/{uuid4()!s}",
            params={"embedding_model_id": str(uuid4())},
            files=files,
        )
