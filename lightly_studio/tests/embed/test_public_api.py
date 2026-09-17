from __future__ import annotations

from pathlib import Path

import numpy as np
from lightly_studio_serve.embedder import Capability, Embedder, ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio import ImageDataset, register_default_embedder
from lightly_studio.embed import embedder_registry, public_api
from lightly_studio.embed.embedder_registry import EmbedderRegistry


def test_register_default_embedder(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)

    public_api.register_default_embedder(embedder=embedder)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=None)


def test_register_default_embedder__bootstrap_for(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)
    bootstrap_for = {Capability.TEXT}

    public_api.register_default_embedder(embedder=embedder, bootstrap_for=bootstrap_for)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=bootstrap_for)


def test_register_default_embedder__embeds_added_images(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """A registered embedder is used to embed images added to a dataset."""
    register_default_embedder(embedder=_FixedImageEmbedder())

    images_path = tmp_path / "images"
    images_path.mkdir()
    _create_sample_images([images_path / "image1.jpg", images_path / "image2.png"])

    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=images_path)

    samples = dataset.query().to_list()
    assert len(samples) == 2
    for sample in samples:
        embeddings = sample.sample_table.embeddings
        assert len(embeddings) == 1
        # The vector comes from the registered embedder: its dimension and value.
        assert embeddings[0].embedding.shape == (_EMBEDDING_DIMENSION,)
        assert np.array_equal(embeddings[0].embedding, np.ones(_EMBEDDING_DIMENSION))


_EMBEDDING_DIMENSION = 7


class _FixedImageEmbedder(ImagePathEmbedder):
    """Image embedder that returns a fixed all-ones vector for every image."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="fixed_model", dimension=_EMBEDDING_DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        embeddings = np.ones((len(paths), _EMBEDDING_DIMENSION), dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(paths))))


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)
