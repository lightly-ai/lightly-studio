"""Shared helper for batched image-crop embedding."""

from __future__ import annotations

from typing import Any

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.image_embedding import EmbeddingContext


def embed_image_crops_batched(
    image_crops: list[ImageCrop],
    context: EmbeddingContext,
    show_progress: bool,
) -> NDArray[np.float32]:
    """Embed image crops, opening each source file once and preserving input order.

    Args:
        image_crops: Crop definitions to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Float32 array of shape ``(len(image_crops), embedding_dimension)``.
    """
    total_crops = len(image_crops)
    if not total_crops:
        return np.empty((0, context.embedding_dimension), dtype=np.float32)

    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    crops_by_filepath: dict[str, list[tuple[int, ImageCrop]]] = {}
    for index, image_crop in enumerate(image_crops):
        crops_by_filepath.setdefault(image_crop.filepath, []).append((index, image_crop))

    embeddings = np.empty((total_crops, context.embedding_dimension), dtype=np.float32)
    # Reusable batch buffer, lazily sized from the first preprocessed crop.
    batch_buffer: torch.Tensor | None = None
    batch_indices: list[int] = []

    with (
        tqdm(
            total=total_crops,
            desc="Generating crop embeddings",
            unit=" crops",
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        for filepath, indexed_crops in crops_by_filepath.items():
            with fsspec.open(filepath, "rb") as file:
                image = Image.open(file).convert("RGB")
                for index, image_crop in indexed_crops:
                    cropped = image.crop(
                        (
                            image_crop.x,
                            image_crop.y,
                            image_crop.x + image_crop.width,
                            image_crop.y + image_crop.height,
                        )
                    )
                    preprocessed = context.preprocess(cropped)
                    if batch_buffer is None:
                        batch_buffer = torch.empty(
                            (context.max_batch_size, *preprocessed.shape),
                            dtype=preprocessed.dtype,
                        )
                    batch_buffer[len(batch_indices)] = preprocessed
                    batch_indices.append(index)
                    if len(batch_indices) >= context.max_batch_size:
                        _flush_crop_batch(
                            batch_buffer=batch_buffer,
                            batch_indices=batch_indices,
                            embeddings=embeddings,
                            context=context,
                            progress_bar=progress_bar,
                        )

        _flush_crop_batch(
            batch_buffer=batch_buffer,
            batch_indices=batch_indices,
            embeddings=embeddings,
            context=context,
            progress_bar=progress_bar,
        )

    return embeddings


def _flush_crop_batch(
    batch_buffer: torch.Tensor | None,
    batch_indices: list[int],
    embeddings: NDArray[np.float32],
    context: EmbeddingContext,
    progress_bar: Any,
) -> None:
    """Encode the current crop batch and write results into ``embeddings``."""
    if batch_buffer is None or not batch_indices:
        return
    filled = len(batch_indices)
    images_tensor = batch_buffer[:filled].to(context.device, non_blocking=True)
    batch_embeddings = context.encode_batch(images_tensor)
    for batch_position, crop_index in enumerate(batch_indices):
        embeddings[crop_index] = batch_embeddings[batch_position]
    progress_bar.update(filled)
    batch_indices.clear()
