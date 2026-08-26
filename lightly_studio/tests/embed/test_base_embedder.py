from __future__ import annotations

import numpy as np

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder, derive_capabilities
from lightly_studio.embed.capability import Capability


def _zeros_result(count: int) -> EmbeddingResult:
    return EmbeddingResult(
        embeddings=np.zeros((count, 2), dtype=np.float32), kept_indices=list(range(count))
    )


class _NothingEmbedder:
    """Implements no capability protocol."""


class _OnlyText:
    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _zeros_result(len(texts))


class _TextAndImage:
    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _zeros_result(len(texts))

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return _zeros_result(len(paths))


def test_derive_capabilities__none() -> None:
    assert derive_capabilities(_NothingEmbedder()) == frozenset()


def test_derive_capabilities__single() -> None:
    assert derive_capabilities(_OnlyText()) == frozenset({Capability.TEXT})


def test_derive_capabilities__multiple() -> None:
    assert derive_capabilities(_TextAndImage()) == frozenset(
        {Capability.TEXT, Capability.IMAGE_PATH}
    )


class TestBaseEmbedder:
    def test_descriptor(self) -> None:
        class _Plain(BaseEmbedder):
            pass

        descriptor = _Plain()._descriptor(model_id="my_model", dimension=7)

        assert descriptor.model_id == "my_model"
        assert descriptor.dimension == 7
        # A base subclass with no capability protocol implements none.
        assert descriptor.capabilities == frozenset()

    def test_descriptor__derives_subclass_capabilities(self) -> None:
        class _ImageOnly(BaseEmbedder):
            def embed_images(self, paths: list[str]) -> EmbeddingResult:
                return EmbeddingResult(
                    embeddings=np.zeros((len(paths), 3), dtype=np.float32),
                    kept_indices=list(range(len(paths))),
                )

        descriptor = _ImageOnly()._descriptor(model_id="image_only", dimension=3)

        assert descriptor.capabilities == frozenset({Capability.IMAGE_PATH})
