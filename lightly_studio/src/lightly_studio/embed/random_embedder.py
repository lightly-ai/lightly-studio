"""Embedder that returns random vectors, useful as a default and for testing."""

from __future__ import annotations

import numpy as np

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder
from lightly_studio.embed.capability import EmbedderDescriptor


class RandomEmbedder(BaseEmbedder):
    """Embedder that returns random vectors of a fixed dimension.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Implements ``ImagePathEmbedder`` and ``TextEmbedder`` structurally, so
    ``load`` reports ``{IMAGE_PATH, TEXT}``.
    """

    def __init__(self, *, model_id: str = "random", dimension: int = 3) -> None:
        """Initialize the random embedder.

        Args:
            model_id: Stable identity string for the embedder.
            dimension: Length of the random embedding vectors to generate.
        """
        self._model_id = model_id
        self._dimension = dimension

    def load(self) -> EmbedderDescriptor:
        """Return the embedder's identity and derived capabilities."""
        return self._descriptor(model_id=self._model_id, dimension=self._dimension)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Generate random embeddings for image paths."""
        return self._random_result(count=len(paths))

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Generate random embeddings for text inputs."""
        return self._random_result(count=len(texts))

    def _random_result(self, count: int) -> EmbeddingResult:
        embeddings = np.random.rand(count, self._dimension).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))
