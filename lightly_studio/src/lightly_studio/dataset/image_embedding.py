"""Shared helpers for batched image embedding.

Holds the model-agnostic :class:`EmbeddingContext` used across the image and
image-crop embedding paths, plus the batched full-image embedding helper. The
crop-specific path lives in ``image_crop_embedding.py`` and reuses the same
``EmbeddingContext``.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TypeVar

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.utils import batching, parallelize

_ItemT = TypeVar("_ItemT")


@dataclass(frozen=True)
class EmbeddingContext:
    """Model-specific configuration for batched image and image-crop embedding.

    Attributes:
        embedding_dimension: Output embedding dimension.
        max_batch_size: Maximum images/crops encoded per model forward pass.
        device: Torch device for model inference.
        preprocess: Callable that converts a PIL image to a model input tensor.
        encode_batch: Callable that encodes a batch tensor and returns embeddings.
    """

    embedding_dimension: int
    max_batch_size: int
    device: torch.device
    preprocess: Callable[[Image.Image], torch.Tensor]
    encode_batch: Callable[[torch.Tensor], NDArray[np.float32]]


@dataclass(frozen=True)
class _EmbeddingProgress:
    """tqdm label configuration for batched embedding."""

    desc: str
    unit: str


def embed_image_files_batched(
    filepaths: list[str],
    context: EmbeddingContext,
    show_progress: bool,
) -> NDArray[np.float32]:
    """Embed image files in batches, preserving input order.

    Args:
        filepaths: Paths of the images to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Float32 array of shape ``(len(filepaths), embedding_dimension)``.
    """

    def load_and_preprocess(filepath: str) -> torch.Tensor:
        with fsspec.open(filepath, "rb") as file:
            image = Image.open(file).convert("RGB")
            return context.preprocess(image)

    return _embed_items_batched(
        items=filepaths,
        preprocess_item=load_and_preprocess,
        context=context,
        show_progress=show_progress,
        progress=_EmbeddingProgress(desc="Generating embeddings", unit=" images"),
    )


def embed_pil_images_batched(
    images: list[Image.Image],
    context: EmbeddingContext,
    show_progress: bool,
) -> NDArray[np.float32]:
    """Embed in-memory PIL images in batches, preserving input order.

    Args:
        images: PIL images to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Float32 array of shape ``(len(images), embedding_dimension)``.
    """
    return _embed_items_batched(
        items=images,
        preprocess_item=context.preprocess,
        context=context,
        show_progress=show_progress,
        progress=_EmbeddingProgress(desc="Generating frame embeddings", unit=" frames"),
    )


def _embed_items_batched(
    items: Sequence[_ItemT],
    preprocess_item: Callable[[_ItemT], torch.Tensor],
    context: EmbeddingContext,
    show_progress: bool,
    progress: _EmbeddingProgress,
) -> NDArray[np.float32]:
    """Preprocess items on a thread pool and embed them in batches, preserving order.

    ``preprocess_item`` (per-item PIL decode/resize/normalize, plus remote reads for file
    inputs) runs on a bounded thread pool, overlapping that CPU-bound work with GPU/MPS
    inference. Inference (``encode_batch``) runs only here on the calling thread, so the
    model is never touched concurrently; ``thread_imap_lazy`` preserves input order and
    caps the items in flight, keeping embeddings aligned to ``items`` and memory bounded.
    """
    total_items = len(items)
    if not total_items:
        return np.empty((0, context.embedding_dimension), dtype=np.float32)

    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    preprocessed_tensors = parallelize.thread_imap_lazy(
        function=preprocess_item,
        iterable=items,
        max_workers=_preprocess_workers(),
        # Read at most one extra batch ahead so a full next batch is ready during inference
        # while memory stays bounded to a small multiple of the batch size.
        buffer_size=2 * context.max_batch_size,
    )
    return _encode_preprocessed_batches(
        preprocessed_tensors=preprocessed_tensors,
        total_items=total_items,
        context=context,
        show_progress=show_progress,
        progress=progress,
    )


def _encode_preprocessed_batches(
    preprocessed_tensors: Iterable[torch.Tensor],
    total_items: int,
    context: EmbeddingContext,
    show_progress: bool,
    progress: _EmbeddingProgress,
) -> NDArray[np.float32]:
    """Stack the preprocessed tensor stream into batches and run inference, preserving order."""
    embeddings = np.empty((total_items, context.embedding_dimension), dtype=np.float32)
    position = 0
    with (
        tqdm(
            total=total_items,
            desc=progress.desc,
            unit=progress.unit,
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        for batch in batching.batched(preprocessed_tensors, batch_size=context.max_batch_size):
            images_tensor = torch.stack(batch).to(context.device, non_blocking=True)
            batch_embeddings = context.encode_batch(images_tensor)
            batch_size = images_tensor.size(0)
            embeddings[position : position + batch_size] = batch_embeddings
            position += batch_size
            progress_bar.update(batch_size)

    return embeddings


def _preprocess_workers() -> int:
    """Return the thread count for parallel per-item preprocessing.

    Uses available cores - 1 (at least 1), capped at 16, matching the decode-thread and
    shared-executor conventions elsewhere in the codebase.
    """
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1 or 1, 16))
