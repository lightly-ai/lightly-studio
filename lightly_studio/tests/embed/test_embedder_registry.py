import logging

import numpy as np
import pytest

from lightly_studio.embed.embedder import (
    Embedder,
    ImagePathEmbedder,
    TextEmbedder,
)
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec


class _FakeTextImageEmbedder(TextEmbedder, ImagePathEmbedder):
    def __init__(self, space_key: str) -> None:
        self._space_key = space_key

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=2)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), 2), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 2), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _FakeNoCapabilityEmbedder(Embedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="none", dimension=2)


class TestEmbedderRegistry:
    def test_register(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=embedder)

        assert registry.get_text_embedder(space_key="space-a") is embedder
        assert registry.get_image_path_embedder(space_key="space-a") is embedder

    def test_register__no_capability(self) -> None:
        registry = EmbedderRegistry()

        with pytest.raises(ValueError, match="no capability"):
            registry.register(embedder=_FakeNoCapabilityEmbedder())

    def test_register__replaces_existing(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = EmbedderRegistry()
        first = _FakeTextImageEmbedder(space_key="space-a")
        second = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=first)
        with caplog.at_level(logging.WARNING):
            registry.register(embedder=second)

        assert registry.get_text_embedder(space_key="space-a") is second
        assert "Replacing embedder" in caplog.text

    def test_register__separate_spaces(self) -> None:
        registry = EmbedderRegistry()
        embedder_a = _FakeTextImageEmbedder(space_key="space-a")
        embedder_b = _FakeTextImageEmbedder(space_key="space-b")

        registry.register(embedder=embedder_a)
        registry.register(embedder=embedder_b)

        assert registry.get_text_embedder(space_key="space-a") is embedder_a
        assert registry.get_text_embedder(space_key="space-b") is embedder_b

    def test_get_text_embedder__missing(self) -> None:
        registry = EmbedderRegistry()

        assert registry.get_text_embedder(space_key="space-a") is None

    def test_get_image_bytes_embedder__capability_not_implemented(self) -> None:
        registry = EmbedderRegistry()
        registry.register(embedder=_FakeTextImageEmbedder(space_key="space-a"))

        assert registry.get_image_bytes_embedder(space_key="space-a") is None
