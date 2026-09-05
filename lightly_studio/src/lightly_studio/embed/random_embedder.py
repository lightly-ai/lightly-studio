"""Embedder that produces random vectors.

Implements every locally implemented capability so it can stand in for a real model
in tests, demos and local development. The vectors carry no meaning, so search
results are random.
"""

from __future__ import annotations

import numpy as np
from PIL.Image import Image

from lightly_studio.embed.embedder import (
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop


class RandomEmbedder(
    ImagePathEmbedder,
    ImageCropPathEmbedder,
    VideoPathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    ImageBytesEmbedder,
):
    """Embedder that returns a random vector for every input.

    Supports every locally implemented capability. The vectors are meaningless, so it
    is meant for tests, demos and local development, not for real search.
    """

    __slots__ = ("_dimension",)

    def __init__(self, dimension: int = 3) -> None:
        """Create a random embedder.

        Args:
            dimension: Length of each embedding vector.
        """
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the random embedding space."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=self._dimension)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Return a random vector for each image path."""
        return self._random_result(count=len(paths))

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Return a random vector for each crop."""
        return self._random_result(count=len(crops))

    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        """Return a random vector for each video path."""
        return self._random_result(count=len(paths))

    def embed_frames(self, frames: list[Image]) -> EmbeddingResult:
        """Return a random vector for each frame."""
        return self._random_result(count=len(frames))

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Return a random vector for each text string."""
        return self._random_result(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Return a random vector for each image given as bytes."""
        return self._random_result(count=len(images))

    def _random_result(self, count: int) -> EmbeddingResult:
        embeddings = np.random.rand(count, self._dimension).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))
