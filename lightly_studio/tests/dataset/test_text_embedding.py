"""Unit tests for batched text embedding."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
import pytest
import torch
from numpy.typing import NDArray

from lightly_studio.dataset import text_embedding
from lightly_studio.dataset.embedding_generator import (
    BatchTextEmbeddingGenerator,
    EmbeddingGenerator,
    RandomEmbeddingGenerator,
)
from lightly_studio.dataset.text_embedding import TextEmbeddingContext
from lightly_studio.models.embedding_model import EmbeddingModelCreate

_DIMENSION = 3


class _TextLengthGenerator(EmbeddingGenerator):
    """Generator without a batched text path, embedding a text by its length."""

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        return EmbeddingModelCreate(
            name="TextLength",
            embedding_model_hash="text_length_model",
            embedding_dimension=_DIMENSION,
            collection_id=collection_id,
        )

    def embed_text(self, text: str) -> list[float]:
        return [float(len(text))] * _DIMENSION


def test_embed_texts__uses_batched_path() -> None:
    """A generator implementing the batched protocol embeds all texts at once."""
    generator = RandomEmbeddingGenerator(dimension=_DIMENSION)
    assert isinstance(generator, BatchTextEmbeddingGenerator)

    embeddings = text_embedding.embed_texts(
        generator=generator, texts=["a", "b"], show_progress=False
    )

    assert embeddings.shape == (2, _DIMENSION)


def test_embed_texts__falls_back_to_single_text_path() -> None:
    """A generator without a batched path embeds one text per call, in input order."""
    generator = _TextLengthGenerator()
    assert not isinstance(generator, BatchTextEmbeddingGenerator)

    embeddings = text_embedding.embed_texts(
        generator=generator, texts=["a", "bbb"], show_progress=False
    )

    assert embeddings.dtype == np.float32
    np.testing.assert_array_equal(embeddings, np.array([[1.0] * _DIMENSION, [3.0] * _DIMENSION]))


def test_embed_texts__raises_on_empty_texts() -> None:
    generator = RandomEmbeddingGenerator(dimension=_DIMENSION)
    with pytest.raises(ValueError, match=r"texts must not be empty."):
        text_embedding.embed_texts(generator=generator, texts=[], show_progress=False)


def test_embed_texts_batched__preserves_order_across_batches() -> None:
    """Texts are embedded in input order even when they span multiple batches."""
    texts = ["one", "two", "three", "four", "five"]
    embeddings = text_embedding.embed_texts_batched(
        texts=texts,
        context=_length_context(max_batch_size=2),
        show_progress=False,
    )

    assert embeddings.shape == (len(texts), _DIMENSION)
    expected = np.array([[float(len(text))] * _DIMENSION for text in texts], dtype=np.float32)
    np.testing.assert_array_equal(embeddings, expected)


def test_embed_texts_batched__returns_empty_for_no_texts() -> None:
    embeddings = text_embedding.embed_texts_batched(
        texts=[], context=_length_context(max_batch_size=2), show_progress=False
    )
    assert embeddings.shape == (0, _DIMENSION)


def test_embed_texts_batched__raises_on_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match=r"max_batch_size must be positive."):
        text_embedding.embed_texts_batched(
            texts=["one"], context=_length_context(max_batch_size=0), show_progress=False
        )


def _length_context(max_batch_size: int) -> TextEmbeddingContext:
    """Build a context whose "model" encodes a text as its repeated length."""

    def tokenize(texts: Sequence[str]) -> torch.Tensor:
        return torch.tensor([[len(text)] for text in texts], dtype=torch.float32)

    def encode_batch(tokens: torch.Tensor) -> NDArray[np.float32]:
        return tokens.repeat(1, _DIMENSION).numpy().astype(np.float32)

    return TextEmbeddingContext(
        embedding_dimension=_DIMENSION,
        max_batch_size=max_batch_size,
        device=torch.device("cpu"),
        tokenize=tokenize,
        encode_batch=encode_batch,
    )
