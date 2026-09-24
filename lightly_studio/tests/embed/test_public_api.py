from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImagePathEmbedder,
    TextEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import ImageDataset
from lightly_studio.embed import embed_samples, embedder_registry, public_api
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.errors import RemoteEmbedderConfigError
from lightly_studio.resolvers import collection_embedding_model_resolver, embedding_model_resolver

_EMBEDDING_DIMENSION = 7


class _FixedImageEmbedder(ImagePathEmbedder):
    """Image embedder that returns a fixed all-ones vector for every image."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="fixed_model", dimension=_EMBEDDING_DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        embeddings = np.ones((len(paths), _EMBEDDING_DIMENSION), dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(paths))))


class _ServerEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Server-side embedder that returns an all-twos vector for every text and image."""

    def __init__(self, space_key: str = "fixed_model", dimension: int = _EMBEDDING_DIMENSION):
        self._spec = EmbeddingSpaceSpec(space_key=space_key, dimension=dimension)

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return self._spec

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return self._twos(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return self._twos(count=len(images))

    def _twos(self, count: int) -> EmbeddingResult:
        embeddings = np.full((count, self._spec.dimension), 2.0, dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))


def test_register_default_embedder(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)

    public_api.register_default_embedder(embedder=embedder)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=None)


def test_register_default_embedder__for_capabilities(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)
    for_capabilities = {Capability.TEXT}

    public_api.register_default_embedder(embedder=embedder, for_capabilities=for_capabilities)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=for_capabilities)


@pytest.mark.usefixtures("patch_collection")
def test_register_default_embedder__embeds_added_images(tmp_path: Path) -> None:
    """A registered embedder is used to embed images added to a dataset."""
    lightly_studio.register_default_embedder(embedder=_FixedImageEmbedder())

    images_path = tmp_path / "images"
    images_path.mkdir()
    Image.new("RGB", (10, 10)).save(images_path / "image1.jpg")
    Image.new("RGB", (10, 10)).save(images_path / "image2.png")

    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=images_path)

    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )
    assert default_model is not None
    assert default_model.name == "fixed_model"

    samples = dataset.query().to_list()
    assert len(samples) == 2
    for sample in samples:
        embeddings = sample.sample_table.embeddings
        assert len(embeddings) == 1
        # The embedding is linked to the registered embedder's model.
        assert embeddings[0].embedding_model_id == default_model.embedding_model_id
        # The vector comes from the registered embedder: its dimension and value.
        assert embeddings[0].embedding.shape == (_EMBEDDING_DIMENSION,)
        assert np.array_equal(embeddings[0].embedding, np.ones(_EMBEDDING_DIMENSION))


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_embedder(tmp_path: Path, mocker: MockerFixture) -> None:
    dataset = _create_dataset(tmp_path=tmp_path)
    _serve(embedder=_ServerEmbedder(), mocker=mocker)

    lightly_studio.register_remote_embedder(
        dataset=dataset, url="http://embedder.test", api_key="k"
    )

    text_embedding = embed_samples.embed_text_for_collection(
        session=dataset.session, collection_id=dataset.collection_id, text="a cat"
    )
    image_embedding = embed_samples.embed_image_for_collection(
        session=dataset.session, collection_id=dataset.collection_id, image_bytes=_png_bytes()
    )
    assert text_embedding == [2.0] * _EMBEDDING_DIMENSION
    assert image_embedding == [2.0] * _EMBEDDING_DIMENSION


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_embedder__dimension_mismatch(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path)
    _serve(embedder=_ServerEmbedder(dimension=_EMBEDDING_DIMENSION + 1), mocker=mocker)

    with pytest.raises(RemoteEmbedderConfigError, match=r"dimension 8"):
        lightly_studio.register_remote_embedder(dataset=dataset, url="http://embedder.test")

    _assert_no_remote_embedder(dataset=dataset)


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_embedder__unknown_space(tmp_path: Path, mocker: MockerFixture) -> None:
    dataset = _create_dataset(tmp_path=tmp_path)
    _serve(embedder=_ServerEmbedder(space_key="other_model"), mocker=mocker)

    with pytest.raises(
        RemoteEmbedderConfigError, match=r"'other_model'.*Known spaces: \['fixed_model'\]"
    ):
        lightly_studio.register_remote_embedder(dataset=dataset, url="http://embedder.test")

    _assert_no_remote_embedder(dataset=dataset)


def _create_dataset(tmp_path: Path) -> ImageDataset:
    """Create a dataset embedded with a precalculated embedder in the ``fixed_model`` space."""
    lightly_studio.register_default_embedder(embedder=_FixedImageEmbedder())
    Image.new("RGB", (10, 10)).save(tmp_path / "image.png")
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=tmp_path)
    return dataset


def _serve(embedder: Embedder, mocker: MockerFixture) -> None:
    """Serve ``embedder`` to every client that ``connection.build_client`` opens."""
    mocker.patch.object(
        connection,
        "build_client",
        side_effect=lambda url: TestClient(
            server.create_app(embedder=embedder), base_url=url, follow_redirects=False
        ),
    )


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def _assert_no_remote_embedder(dataset: ImageDataset) -> None:
    (embedding_model,) = embedding_model_resolver.get_all_by_dataset_id(
        session=dataset.session, dataset_id=dataset.dataset_id
    )
    assert embedding_model.remote_embedder_url is None
    assert embedding_model.api_key is None
