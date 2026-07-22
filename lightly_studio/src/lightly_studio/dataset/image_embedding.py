"""Shared helpers for batched image embedding.

Holds the model-agnostic :class:`EmbeddingContext` used across the image and
image-crop embedding paths, plus the batched full-image embedding helper. The
crop-specific path lives in ``image_crop_embedding.py`` and reuses the same
``EmbeddingContext``.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TypeVar

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import FileOutcome, FileOutcomeReport
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


@dataclass(frozen=True)
class ImageEmbeddingResult:
    """Embeddings for the image files that could be read, plus which inputs they cover.

    Broken files (unreadable/undecodable) are skipped rather than aborting the whole
    run, so ``embeddings`` may hold fewer rows than the input file list. ``kept_indices``
    maps each row back to its position in the input list, in input order, letting callers
    realign any parallel per-file data (e.g. sample IDs) with the embeddings.

    Attributes:
        embeddings: Float32 array of shape ``(len(kept_indices), embedding_dimension)``.
        kept_indices: Indices into the input file list of the files that were embedded,
            in input order.
    """

    embeddings: NDArray[np.float32]
    kept_indices: list[int]


def embed_image_files_batched(
    filepaths: list[str],
    context: EmbeddingContext,
    show_progress: bool,
) -> ImageEmbeddingResult:
    """Embed image files in batches, preserving input order and skipping broken files.

    Args:
        filepaths: Paths of the images to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        An ``ImageEmbeddingResult`` whose embeddings cover only the readable files, with
        ``kept_indices`` mapping each row back to its input position.

    Raises:
        AllInputFilesFailedError: If at least one file was attempted and every attempted
            file was broken (i.e. no file could be read and embedded).
        ValueError: If ``context.max_batch_size`` is not positive.
    """

    def load_and_preprocess(filepath: str) -> torch.Tensor | None:
        try:
            with fsspec.open(filepath, "rb") as file:
                image = Image.open(file).convert("RGB")
        except (OSError, UnidentifiedImageError):
            return None
        return context.preprocess(image)

    result = _embed_items_batched(
        items=filepaths,
        preprocess_item=load_and_preprocess,
        context=context,
        show_progress=show_progress,
        progress=_EmbeddingProgress(desc="Generating embeddings", unit=" images"),
    )

    kept_indices_set = set(result.kept_indices)
    report = FileOutcomeReport()
    for index, filepath in enumerate(filepaths):
        outcome = FileOutcome.ADDED if index in kept_indices_set else FileOutcome.BROKEN
        report.record(path=filepath, outcome=outcome)
    report.raise_if_all_failed()
    report.log_summary()

    return result


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
    result = _embed_items_batched(
        items=images,
        preprocess_item=context.preprocess,
        context=context,
        show_progress=show_progress,
        progress=_EmbeddingProgress(desc="Generating frame embeddings", unit=" frames"),
    )
    return result.embeddings


def _embed_items_batched(
    items: Sequence[_ItemT],
    preprocess_item: Callable[[_ItemT], torch.Tensor | None],
    context: EmbeddingContext,
    show_progress: bool,
    progress: _EmbeddingProgress,
) -> ImageEmbeddingResult:
    """Preprocess items on a thread pool and embed them in batches, preserving order.

    ``preprocess_item`` (per-item PIL decode/resize/normalize, plus remote reads for file
    inputs) runs on a bounded thread pool, overlapping that CPU-bound work with GPU/MPS
    inference. It returns ``None`` for an item that should be skipped (e.g. an unreadable
    file); such items are dropped before batching. Inference (``encode_batch``) runs only here on
    the calling thread, so the model is never touched concurrently; ``thread_imap_lazy`` preserves
    input order and caps the items in flight, keeping embeddings aligned to ``items`` and memory
    bounded.

    Returns:
        An ``ImageEmbeddingResult`` whose embeddings cover the kept items and whose
        ``kept_indices`` map each row back to its index into ``items``, both in input order.
    """
    total_items = len(items)
    if not total_items:
        empty = np.empty((0, context.embedding_dimension), dtype=np.float32)
        return ImageEmbeddingResult(embeddings=empty, kept_indices=[])

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
    # Drop skipped items before batching, recording which input indices survive.
    kept_indices: list[int] = []
    kept_tensors_iter = _keep_non_none(tensors=preprocessed_tensors, out_kept_indices=kept_indices)
    embeddings = _encode_preprocessed_batches(
        preprocessed_tensors=kept_tensors_iter,
        max_items=total_items,
        context=context,
        show_progress=show_progress,
        progress=progress,
    )
    return ImageEmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


def _keep_non_none(
    tensors: Iterable[torch.Tensor | None],
    out_kept_indices: list[int],
) -> Iterator[torch.Tensor]:
    """Yield the non-``None`` tensors, recording their input indices as they are consumed.

    Args:
        tensors: The preprocessed tensor stream, with ``None`` marking a skipped item.
        out_kept_indices: Output list, mutated in place. As the returned iterator is
            consumed, the input index of each yielded (non-``None``) tensor is appended, in
            input order. It is empty until iteration starts and complete once the iterator is
            exhausted, so callers must finish consuming before reading it.
    """
    for index, tensor in enumerate(tensors):
        if tensor is not None:
            out_kept_indices.append(index)
            yield tensor


def _encode_preprocessed_batches(
    preprocessed_tensors: Iterable[torch.Tensor],
    max_items: int,
    context: EmbeddingContext,
    show_progress: bool,
    progress: _EmbeddingProgress,
) -> NDArray[np.float32]:
    """Stack the preprocessed tensor stream into batches and run inference, preserving order.

    ``max_items`` is an upper bound on the number of embeddings (the input count before any
    skips); the returned array is truncated to the number of tensors actually encoded.
    """
    embeddings = np.empty((max_items, context.embedding_dimension), dtype=np.float32)
    position = 0
    with (
        tqdm(
            total=max_items,
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

    # Truncate to the number of tensors actually encoded (``max_items`` was an upper bound).
    return embeddings[:position]


def _preprocess_workers() -> int:
    """Return the thread count for parallel per-item preprocessing.

    Uses available cores - 1 (at least 1), capped at 16, matching the decode-thread and
    shared-executor conventions elsewhere in the codebase.
    """
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1 or 1, 16))
