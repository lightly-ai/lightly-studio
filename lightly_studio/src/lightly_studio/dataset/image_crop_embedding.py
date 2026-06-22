"""Shared helper for batched image-crop embedding."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.dataset.embedding_generator import ImageCrop


def embed_image_crops_batched(  # noqa: PLR0913
    image_crops: list[ImageCrop],
    embedding_dimension: int,
    max_batch_size: int,
    device: torch.device,
    preprocess: Callable[[Image.Image], torch.Tensor],
    encode_batch: Callable[[torch.Tensor], NDArray[np.float32]],
    show_progress: bool,
) -> NDArray[np.float32]:
    """Embed image crops, opening each source file once and preserving input order.

    Args:
        image_crops: Crop definitions to embed.
        embedding_dimension: Output embedding width.
        max_batch_size: Maximum crops encoded per model forward pass.
        device: Torch device for model inference.
        preprocess: Callable that converts a PIL crop to a model input tensor.
        encode_batch: Callable that encodes a batch tensor and returns embeddings.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        Float32 array of shape ``(len(image_crops), embedding_dimension)``.
    """
    total_crops = len(image_crops)
    if not total_crops:
        return np.empty((0, embedding_dimension), dtype=np.float32)

    crops_by_filepath: dict[str, list[tuple[int, ImageCrop]]] = {}
    for index, image_crop in enumerate(image_crops):
        crops_by_filepath.setdefault(image_crop.filepath, []).append((index, image_crop))

    embeddings = np.empty((total_crops, embedding_dimension), dtype=np.float32)
    batch_tensors: list[torch.Tensor] = []
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
                    batch_tensors.append(preprocess(cropped))
                    batch_indices.append(index)
                    if len(batch_tensors) >= max_batch_size:
                        _flush_crop_batch(
                            batch_tensors,
                            batch_indices,
                            embeddings,
                            device,
                            encode_batch,
                            progress_bar,
                        )

        _flush_crop_batch(
            batch_tensors,
            batch_indices,
            embeddings,
            device,
            encode_batch,
            progress_bar,
        )

    return embeddings


def _flush_crop_batch(  # noqa: PLR0913
    batch_tensors: list[torch.Tensor],
    batch_indices: list[int],
    embeddings: NDArray[np.float32],
    device: torch.device,
    encode_batch: Callable[[torch.Tensor], NDArray[np.float32]],
    progress_bar: Any,
) -> None:
    if not batch_tensors:
        return
    images_tensor = torch.stack(batch_tensors).to(device, non_blocking=True)
    batch_embeddings = encode_batch(images_tensor)
    for batch_position, crop_index in enumerate(batch_indices):
        embeddings[crop_index] = batch_embeddings[batch_position]
    progress_bar.update(len(batch_tensors))
    batch_tensors.clear()
    batch_indices.clear()
