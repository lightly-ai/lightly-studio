from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.remote.embedder import RemoteEmbedder

SPACE_KEY = "acme/model@v1"
DIMENSION = 2


class _TextImageEmbedder(TextEmbedder, ImageBytesEmbedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _result(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _result(count=len(images))


class TestRemoteEmbedder:
    def test_connect_and_embed(self) -> None:
        with TestClient(server.create_app(embedder=_TextImageEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            assert isinstance(remote, ImageBytesEmbedder)
            result = remote.embed_text(texts=["first", "second"])

        assert result.kept_indices == [0, 1]
        np.testing.assert_array_equal(result.embeddings, np.array([[0.5, -0.5]] * 2))

    def test_register_and_resolve(self) -> None:
        with TestClient(server.create_app(embedder=_TextImageEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        registry = EmbedderRegistry()
        registry.register(embedder=remote)
        text_embedder: object = registry.get_text_embedder()
        image_embedder: object = registry.get_image_bytes_embedder()

        assert text_embedder is remote
        assert image_embedder is remote


def _result(count: int) -> EmbeddingResult:
    embeddings = np.array([[0.5, -0.5]] * count, dtype=np.float32).reshape(count, DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))
