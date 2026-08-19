from __future__ import annotations

import numpy as np

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.registry import EmbedderRegistry


class _TextOnlyEmbedder(BaseEmbedder):
    def __init__(self) -> None:
        super().__init__(model_id="text_only", dimension=3)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), 3), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )


class TestEmbedderRegistry:
    def test_register__routes_by_capability(self) -> None:
        registry = EmbedderRegistry()
        random_embedder = RandomEmbedder()

        registry.register(random_embedder)

        assert registry.get_default_image_path_embedder() is random_embedder
        assert registry.get_default_text_embedder() is random_embedder

    def test_register__only_fills_offered_slots(self) -> None:
        registry = EmbedderRegistry()
        text_embedder = _TextOnlyEmbedder()

        registry.register(text_embedder)

        assert registry.get_default_text_embedder() is text_embedder
        assert registry.get_default_image_path_embedder() is None

    def test_get_defaults__empty_registry(self) -> None:
        registry = EmbedderRegistry()

        assert registry.get_default_text_embedder() is None
        assert registry.get_default_image_path_embedder() is None
