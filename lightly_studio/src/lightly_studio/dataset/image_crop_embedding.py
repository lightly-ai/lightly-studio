"""Shared helper for batched image-crop embedding."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.dataset.embedding_generator import BatchedEmbeddingResult, ImageCrop
from lightly_studio.dataset.image_embedding import EmbeddingContext


@dataclass
class _CropEmbeddingOutput:
    """Tracks the preallocated output array and the next write position."""

    embeddings: NDArray[np.float32]
    keys: list[UUID] = field(default_factory=list)
    position: int = 0


def embed_image_crops_batched(
    keyed_crops: Sequence[tuple[UUID, ImageCrop]],
    context: EmbeddingContext,
    show_progress: bool,
) -> BatchedEmbeddingResult:
    """Embed image crops, opening each source file once.

    Each embedding is tagged with the sample id paired with its crop, so callers
    map results back by identity rather than by position.

    Args:
        keyed_crops: ``(sample_id, crop)`` pairs to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Embeddings for the embedded crops, keyed by sample id.
    """
    total_crops = len(keyed_crops)
    if not total_crops:
        return BatchedEmbeddingResult(
            embeddings=np.empty((0, context.embedding_dimension), dtype=np.float32),
            keys=[],
        )

    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    crops_by_filepath: dict[str, list[tuple[UUID, ImageCrop]]] = {}
    for key, image_crop in keyed_crops:
        crops_by_filepath.setdefault(image_crop.filepath, []).append((key, image_crop))

    # Reusable batch buffer, lazily sized from the first preprocessed crop.
    batch_buffer: torch.Tensor | None = None
    batch_keys: list[UUID] = []
    output = _CropEmbeddingOutput(
        embeddings=np.empty((total_crops, context.embedding_dimension), dtype=np.float32)
    )

    with (
        tqdm(
            total=total_crops,
            desc="Generating crop embeddings",
            unit=" crops",
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        for filepath, keyed_group in crops_by_filepath.items():
            with fsspec.open(filepath, "rb") as file:
                image = Image.open(file).convert("RGB")
                for key, image_crop in keyed_group:
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
                    batch_buffer[len(batch_keys)] = preprocessed
                    batch_keys.append(key)
                    if len(batch_keys) >= context.max_batch_size:
                        _flush_crop_batch(
                            batch_buffer=batch_buffer,
                            batch_keys=batch_keys,
                            output=output,
                            context=context,
                            progress_bar=progress_bar,
                        )

        _flush_crop_batch(
            batch_buffer=batch_buffer,
            batch_keys=batch_keys,
            output=output,
            context=context,
            progress_bar=progress_bar,
        )

    return BatchedEmbeddingResult(
        embeddings=output.embeddings[: output.position],
        keys=output.keys,
    )


def _flush_crop_batch(
    batch_buffer: torch.Tensor | None,
    batch_keys: list[UUID],
    output: _CropEmbeddingOutput,
    context: EmbeddingContext,
    progress_bar: Any,
) -> None:
    """Encode the current crop batch and write results into ``embeddings``."""
    if batch_buffer is None or not batch_keys:
        return
    filled = len(batch_keys)
    images_tensor = batch_buffer[:filled].to(context.device, non_blocking=True)
    batch_embeddings = context.encode_batch(images_tensor)
    next_position = output.position + filled
    output.embeddings[output.position : next_position] = batch_embeddings
    output.position = next_position
    output.keys.extend(batch_keys)
    progress_bar.update(filled)
    batch_keys.clear()
