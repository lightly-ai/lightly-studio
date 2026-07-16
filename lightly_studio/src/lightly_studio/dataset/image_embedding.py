"""Shared helpers for batched image embedding.

Holds the model-agnostic :class:`EmbeddingContext` used across the image and
image-crop embedding paths, plus the batched full-image embedding helper. The
crop-specific path lives in ``image_crop_embedding.py`` and reuses the same
``EmbeddingContext``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm


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


class _PILImageDataset(Dataset[torch.Tensor]):
    """Dataset wrapping in-memory PIL images and a preprocess function."""

    def __init__(
        self,
        images: list[Image.Image],
        preprocess: Callable[[Image.Image], torch.Tensor],
    ) -> None:
        self.images = images
        self.preprocess = preprocess

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.preprocess(self.images[idx])


class _ImageFileDataset(Dataset[torch.Tensor]):
    """Dataset wrapping image file paths and a preprocess function.

    Used for efficient batched image loading and preprocessing.
    """

    def __init__(
        self,
        filepaths: list[str],
        preprocess: Callable[[Image.Image], torch.Tensor],
    ) -> None:
        self.filepaths = filepaths
        self.preprocess = preprocess

    def __len__(self) -> int:
        return len(self.filepaths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        with fsspec.open(self.filepaths[idx], "rb") as file:
            image = Image.open(file).convert("RGB")
            return self.preprocess(image)


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
    return _embed_dataset_batched(
        _ImageFileDataset(filepaths, context.preprocess),
        len(filepaths),
        context,
        show_progress,
        _EmbeddingProgress(desc="Generating embeddings", unit=" images"),
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
    return _embed_dataset_batched(
        _PILImageDataset(images, context.preprocess),
        len(images),
        context,
        show_progress,
        _EmbeddingProgress(desc="Generating frame embeddings", unit=" frames"),
    )


def _embed_dataset_batched(
    dataset: Dataset[torch.Tensor],
    total_images: int,
    context: EmbeddingContext,
    show_progress: bool,
    progress: _EmbeddingProgress,
) -> NDArray[np.float32]:
    """Embed items from a preprocessed image dataset in batches, preserving order."""
    if not total_images:
        return np.empty((0, context.embedding_dimension), dtype=np.float32)

    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    # TODO(Malte, 07/2026): Parallelize per-item preprocessing with
    # parallelize.thread_imap_lazy (each item opens/decodes/preprocesses one image,
    # independently), then group results with batching.batched for the batched forward
    # pass. This overlaps CPU-bound preprocessing (and remote reads) with inference.
    # To avoid issues with db locking and multiprocessing we set the number of
    # workers to 0 (no multiprocessing). The DataLoader is still very useful for
    # batching and async prefetching of images.
    loader = DataLoader(
        dataset,
        batch_size=context.max_batch_size,
        num_workers=0,  # must be 0 to avoid multiprocessing issues
    )

    embeddings = np.empty((total_images, context.embedding_dimension), dtype=np.float32)
    position = 0
    with (
        tqdm(
            total=total_images,
            desc=progress.desc,
            unit=progress.unit,
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        for images_tensor in loader:
            imgs = images_tensor.to(context.device, non_blocking=True)
            batch_embeddings = context.encode_batch(imgs)
            batch_size = imgs.size(0)
            embeddings[position : position + batch_size] = batch_embeddings
            position += batch_size
            progress_bar.update(batch_size)

    return embeddings
