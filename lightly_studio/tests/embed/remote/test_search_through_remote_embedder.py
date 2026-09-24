"""Search a dataset through `register_remote_embedder` against a real embedding server.

The dataset is embedded locally by an embedder that implements no query capability, so
each search has to embed its query on the server.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import lightly_studio
from lightly_studio import ImageDataset
from lightly_studio.api.app import app
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.database import db_manager
from tests.embed.remote import color_embedder, threaded_server
from tests.embed.remote.color_embedder import ColorImagePathEmbedder, ColorQueryEmbedder

_API_KEY = "test-api-key"

# The fixture gives each test its own embedder registry and the test database.
pytestmark = pytest.mark.usefixtures("patch_collection")


@pytest.fixture
def query_embedder() -> ColorQueryEmbedder:
    return ColorQueryEmbedder()


@pytest.fixture
def server_url(query_embedder: ColorQueryEmbedder) -> Iterator[str]:
    with threaded_server.serve(embedder=query_embedder, api_key=_API_KEY) as url:
        yield url


@pytest.fixture
def image_paths(tmp_path: Path) -> dict[str, Path]:
    return color_embedder.write_color_images(directory=tmp_path)


@pytest.fixture
def dataset(image_paths: dict[str, Path], server_url: str) -> ImageDataset:
    lightly_studio.register_default_embedder(embedder=ColorImagePathEmbedder())
    dataset = ImageDataset.create(name="colors")
    dataset.add_images_from_path(path=image_paths["red"].parent)
    lightly_studio.register_remote_embedder(dataset=dataset, url=server_url, api_key=_API_KEY)
    return dataset


@pytest.fixture
def client(dataset: ImageDataset) -> Iterator[TestClient]:
    """A client whose requests use the session of the dataset.

    The test database shares one connection, so a second session cannot open a transaction
    while the dataset session holds one.
    """
    app.dependency_overrides[db_manager._session_dependency] = lambda: dataset.session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_text_search(
    dataset: ImageDataset, query_embedder: ColorQueryEmbedder, client: TestClient
) -> None:
    embedding_response = client.get(
        f"/api/text_embedding/for_collection/{dataset.collection_id}",
        params={"query_text": "red"},
    )

    assert embedding_response.status_code == HTTP_STATUS_OK
    assert query_embedder.call_count == 1
    ranked_file_names = _ranked_file_names(
        client=client, collection_id=dataset.collection_id, embedding=embedding_response.json()
    )
    assert ranked_file_names[0] == "red.png"


def _ranked_file_names(
    client: TestClient, collection_id: UUID, embedding: list[float]
) -> list[str]:
    """List the file names of the collection, most similar to ``embedding`` first."""
    response = client.post(
        f"/api/collections/{collection_id}/images/list",
        json={"text_embedding": embedding},
    )
    assert response.status_code == HTTP_STATUS_OK
    return [sample["file_name"] for sample in response.json()["data"]]
