"""Import a dataset through `register_default_embedder` with a real embedding server.

A restart is a new embedder registry. After it, only the dataset can name the server.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import ImageDataset
from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.resolvers import collection_embedding_model_resolver, sample_embedding_resolver
from tests.embed.remote import color_embedder, threaded_server
from tests.embed.remote.color_embedder import ColorQueryEmbedder

_API_KEY = "test-api-key"

# The fixture gives each test its own embedder registry and the test database.
pytestmark = pytest.mark.usefixtures("patch_collection")

# Another dimension than the one of the color space that the dataset stores
_OTHER_DIMENSION = color_embedder.DIMENSION + 1


class _OtherDimensionColorEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Produces the color space with another dimension."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=color_embedder.SPACE_KEY, dimension=_OTHER_DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _zeros(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _zeros(count=len(images))


@pytest.fixture
def query_embedder() -> ColorQueryEmbedder:
    return ColorQueryEmbedder()


@pytest.fixture
def server_url(query_embedder: ColorQueryEmbedder) -> Iterator[str]:
    with threaded_server.serve(embedder=query_embedder, api_key=_API_KEY) as url:
        yield url


@pytest.fixture
def dataset(server_url: str, tmp_path: Path) -> Iterator[ImageDataset]:
    """A dataset that the server embedded at the import, with one registration only."""
    images = tmp_path / "images"
    images.mkdir()
    color_embedder.write_color_images(directory=images)
    with connection.build_client(url=server_url) as client:
        lightly_studio.register_default_embedder(
            embedder=RemoteEmbedder.connect(client=client, api_key=_API_KEY)
        )
        dataset = ImageDataset.create(name="colors")
        dataset.add_images_from_path(path=images)
        yield dataset


def test_add_images_from_path__stores_the_server(dataset: ImageDataset, server_url: str) -> None:
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )

    assert default_model is not None
    assert default_model.name == color_embedder.SPACE_KEY
    assert default_model.remote_embedder_url == server_url
    assert default_model.api_key == _API_KEY
    embedding_count = sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=dataset.collection_id,
        embedding_model_id=default_model.embedding_model_id,
    )
    assert embedding_count == 3


def test_text_search__after_restart(
    dataset: ImageDataset, query_embedder: ColorQueryEmbedder, mocker: MockerFixture
) -> None:
    call_count = query_embedder.call_count
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    embedding = embed_samples.embed_text_for_collection(
        session=dataset.session, collection_id=dataset.collection_id, text="red"
    )

    # The server embeds a color name as its one-hot vector.
    assert embedding == [1.0, 0.0, 0.0]
    assert query_embedder.call_count == call_count + 1


def test_add_images_from_path__dimension_mismatch_after_restart(
    dataset: ImageDataset, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    more_images = tmp_path / "more"
    more_images.mkdir()
    color_embedder.write_color_images(directory=more_images)

    with (
        threaded_server.serve(embedder=_OtherDimensionColorEmbedder(), api_key=_API_KEY) as url,
        connection.build_client(url=url) as client,
    ):
        lightly_studio.register_default_embedder(
            embedder=RemoteEmbedder.connect(client=client, api_key=_API_KEY)
        )
        with pytest.raises(ValueError, match=r"does not match"):
            dataset.add_images_from_path(path=more_images)
    # The new images are stored without an embedding
    assert len(list(dataset)) == 6
    assert _embedding_count(dataset=dataset) == 3

    # After a restart without the other server, the stored server embeds them
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    dataset.add_images_from_path(path=more_images)

    assert _embedding_count(dataset=dataset) == 6


def _zeros(count: int) -> EmbeddingResult:
    return EmbeddingResult(
        embeddings=np.zeros((count, _OTHER_DIMENSION), dtype=np.float32),
        kept_indices=list(range(count)),
    )


def _embedding_count(dataset: ImageDataset) -> int:
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )
    assert default_model is not None
    return sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=dataset.collection_id,
        embedding_model_id=default_model.embedding_model_id,
    )
