from __future__ import annotations

import numpy as np

from lightly_studio.embed.capability import Capability
from lightly_studio.embed.random_embedder import RandomEmbedder


class TestRandomEmbedder:
    def test_embed_images(self) -> None:
        embedder = RandomEmbedder()

        result = embedder.embed_images(["a.jpg", "b.jpg", "c.jpg"])

        assert result.embeddings.shape == (3, 3)
        assert result.embeddings.dtype == np.float32
        assert result.kept_indices == [0, 1, 2]

    def test_embed_text(self) -> None:
        embedder = RandomEmbedder()

        result = embedder.embed_text(["hello", "world"])

        assert result.embeddings.shape == (2, 3)
        assert result.embeddings.dtype == np.float32
        assert result.kept_indices == [0, 1]

    def test_load(self) -> None:
        descriptor = RandomEmbedder().load()

        assert descriptor.model_id == "random"
        assert descriptor.dimension == 3
        assert descriptor.capabilities == frozenset({Capability.IMAGE_PATH, Capability.TEXT})
