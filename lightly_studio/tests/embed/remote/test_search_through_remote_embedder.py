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
from httpx import Response
from lightly_studio_serve.embedder import ImageBytesEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

import lightly_studio
from lightly_studio import ImageDataset
from lightly_studio.api.app import app
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_OK,
)
from lightly_studio.database import db_manager
from lightly_studio.embed.remote.errors import RemoteEmbedderAuthError
from lightly_studio.resolvers import embedding_model_resolver
from tests.embed.remote import color_embedder, threaded_server
from tests.embed.remote.color_embedder import ColorImagePathEmbedder, ColorQueryEmbedder

_API_KEY = "test-api-key"

# The fixture gives each test its own embedder registry and the test database.
pytestmark = pytest.mark.usefixtures("patch_collection")


class _ImageQueryEmbedder(ImageBytesEmbedder):
    """Embeds an image file for search, and no text."""

    def __init__(self) -> None:
        self._embedder = ColorQueryEmbedder()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return self._embedder.embedding_space_spec()

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return self._embedder.embed_image_bytes(images=images)


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
def local_dataset(image_paths: dict[str, Path]) -> ImageDataset:
    """A dataset embedded locally, with no remote embedder registered."""
    lightly_studio.register_default_embedder(embedder=ColorImagePathEmbedder())
    dataset = ImageDataset.create(name="colors")
    dataset.add_images_from_path(path=image_paths["red"].parent)
    return dataset


@pytest.fixture
def dataset(local_dataset: ImageDataset, server_url: str) -> ImageDataset:
    lightly_studio.register_remote_embedder(dataset=local_dataset, url=server_url, api_key=_API_KEY)
    return local_dataset


@pytest.fixture
def client(local_dataset: ImageDataset) -> Iterator[TestClient]:
    """A client whose requests use the session of the dataset.

    The test database shares one connection, so a second session cannot open a transaction
    while the dataset session holds one.
    """
    app.dependency_overrides[db_manager._session_dependency] = lambda: local_dataset.session
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


def test_image_search(
    dataset: ImageDataset,
    query_embedder: ColorQueryEmbedder,
    image_paths: dict[str, Path],
    client: TestClient,
) -> None:
    embedding_response = client.post(
        f"/api/image_embedding/from_file/for_collection/{dataset.collection_id}",
        files={"file": ("query.png", image_paths["green"].read_bytes(), "image/png")},
    )

    assert embedding_response.status_code == HTTP_STATUS_OK
    # Without the server, the route falls back to the local path embedder.
    assert query_embedder.call_count == 1
    ranked_file_names = _ranked_file_names(
        client=client, collection_id=dataset.collection_id, embedding=embedding_response.json()
    )
    assert ranked_file_names[0] == "green.png"


def test_register_remote_embedder__wrong_api_key(
    local_dataset: ImageDataset, server_url: str
) -> None:
    with pytest.raises(RemoteEmbedderAuthError):
        lightly_studio.register_remote_embedder(
            dataset=local_dataset, url=server_url, api_key="wrong-api-key"
        )

    (embedding_model,) = embedding_model_resolver.get_all_by_dataset_id(
        session=local_dataset.session, dataset_id=local_dataset.dataset_id
    )
    assert embedding_model.remote_embedder_url is None
    assert embedding_model.api_key is None


@pytest.mark.parametrize("query_kind", ["text", "image"])
@pytest.mark.parametrize("queries_before_stop", [0, 1])
def test_search__server_stopped(
    local_dataset: ImageDataset,
    image_paths: dict[str, Path],
    client: TestClient,
    query_kind: str,
    queries_before_stop: int,
) -> None:
    # With no query before the stop, the embedder is built after it. Else it is built before.
    with threaded_server.serve(embedder=ColorQueryEmbedder(), api_key=_API_KEY) as url:
        lightly_studio.register_remote_embedder(dataset=local_dataset, url=url, api_key=_API_KEY)
        for _ in range(queries_before_stop):
            response = _embed_query(
                client=client, dataset=local_dataset, image_paths=image_paths, kind=query_kind
            )
            assert response.status_code == HTTP_STATUS_OK

    response = _embed_query(
        client=client, dataset=local_dataset, image_paths=image_paths, kind=query_kind
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY


def test_text_search__server_without_text(
    local_dataset: ImageDataset, image_paths: dict[str, Path], client: TestClient
) -> None:
    with threaded_server.serve(embedder=_ImageQueryEmbedder(), api_key=_API_KEY) as url:
        lightly_studio.register_remote_embedder(dataset=local_dataset, url=url, api_key=_API_KEY)

        text_response = _embed_query(
            client=client, dataset=local_dataset, image_paths=image_paths, kind="text"
        )
        image_response = _embed_query(
            client=client, dataset=local_dataset, image_paths=image_paths, kind="image"
        )

    assert text_response.status_code == HTTP_STATUS_CONFLICT
    assert "cannot embed text" in text_response.json()["error"]
    # The server is in use, so the conflict is not the one of a space with no server
    assert image_response.status_code == HTTP_STATUS_OK


def _embed_query(
    client: TestClient, dataset: ImageDataset, image_paths: dict[str, Path], kind: str
) -> Response:
    """Embed the text "red" or the green image file as a search query of ``dataset``."""
    if kind == "text":
        return client.get(
            f"/api/text_embedding/for_collection/{dataset.collection_id}",
            params={"query_text": "red"},
        )
    return client.post(
        f"/api/image_embedding/from_file/for_collection/{dataset.collection_id}",
        files={"file": ("query.png", image_paths["green"].read_bytes(), "image/png")},
    )


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
