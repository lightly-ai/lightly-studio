"""Shared helpers for batched text embedding.

Holds the model-agnostic :class:`TextEmbeddingContext` used by the text encoders of the
CLIP-style generators, plus the batched embedding helper built on it. ``embed_texts``
is the entry point for callers: it uses a generator's batched path when it has one and
otherwise falls back to embedding one text per forward pass.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import torch
from numpy.typing import NDArray
from tqdm import tqdm

from lightly_studio.dataset.embedding_generator import (
    BatchTextEmbeddingGenerator,
    EmbeddingGenerator,
)
from lightly_studio.utils import batching


@dataclass(frozen=True)
class TextEmbeddingContext:
    """Model-specific configuration for batched text embedding.

    Attributes:
        embedding_dimension: Output embedding dimension.
        max_batch_size: Maximum texts encoded per model forward pass.
        device: Torch device for model inference.
        tokenize: Callable that converts texts to a model input tensor.
        encode_batch: Callable that encodes a batch tensor and returns embeddings.
    """

    embedding_dimension: int
    max_batch_size: int
    device: torch.device
    tokenize: Callable[[list[str]], torch.Tensor]
    encode_batch: Callable[[torch.Tensor], NDArray[np.float32]]


def embed_texts(
    generator: EmbeddingGenerator,
    texts: Sequence[str],
    show_progress: bool = True,
) -> NDArray[np.float32]:
    """Embed texts with the given generator, preserving input order.

    A generator implementing ``BatchTextEmbeddingGenerator`` encodes the texts in
    batches. Any other generator, e.g. one registered through
    ``set_default_embedding_model``, falls back to ``embed_text`` and encodes one text
    per forward pass.

    Args:
        generator: The generator whose text encoder is used.
        texts: The texts to embed. Must not be empty.
        show_progress: Whether to show a progress bar during embedding.

    Returns:
        Float32 array of shape ``(len(texts), embedding_dimension)``.

    Raises:
        ValueError: If ``texts`` is empty, as the embedding dimension cannot be
            determined without encoding at least one text.
    """
    if not texts:
        raise ValueError("texts must not be empty.")
    if isinstance(generator, BatchTextEmbeddingGenerator):
        return generator.embed_texts(texts=texts, show_progress=show_progress)
    embeddings = [
        generator.embed_text(text)
        for text in tqdm(
            texts,
            desc="Generating text embeddings",
            unit=" texts",
            disable=not show_progress,
        )
    ]
    return np.array(embeddings, dtype=np.float32)


def embed_texts_batched(
    texts: Sequence[str],
    context: TextEmbeddingContext,
    show_progress: bool,
) -> NDArray[np.float32]:
    """Tokenize and encode texts in batches, preserving input order.

    Unlike images, texts need no per-item file reads or decoding, so tokenization is
    cheap enough to run inline with inference instead of on a thread pool.

    Args:
        texts: The texts to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Float32 array of shape ``(len(texts), embedding_dimension)``.

    Raises:
        ValueError: If ``context.max_batch_size`` is not positive.
    """
    embeddings = np.empty((len(texts), context.embedding_dimension), dtype=np.float32)
    if not texts:
        return embeddings
    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    position = 0
    with (
        tqdm(
            total=len(texts),
            desc="Generating text embeddings",
            unit=" texts",
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        for batch in batching.batched(items=texts, batch_size=context.max_batch_size):
            tokens = context.tokenize(batch).to(context.device, non_blocking=True)
            embeddings[position : position + len(batch)] = context.encode_batch(tokens)
            position += len(batch)
            progress_bar.update(len(batch))

    return embeddings
