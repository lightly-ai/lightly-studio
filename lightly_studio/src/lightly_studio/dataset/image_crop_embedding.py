"""Shared helper for batched image-crop embedding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    BROKEN_IMAGE_ERRORS,
    FileOutcome,
    FileOutcomeReport,
)
from lightly_studio.dataset.image_embedding import EmbeddingContext
from lightly_studio.embed.types import EmbeddingResult, ImageCrop
from lightly_studio.utils import executor, parallelize


@dataclass(frozen=True)
class _SourceImageCrops:
    """Crops from one source image, with their positions in the input list."""

    filepath: str
    indexed_crops: list[tuple[int, ImageCrop]]


@dataclass(frozen=True)
class _LoadedSourceImageCrops:
    """Loaded source image and its crops, or ``None`` for a broken image."""

    filepath: str
    indexed_crops: list[tuple[int, ImageCrop]]
    image: Image.Image | None


def embed_image_crops_batched(
    image_crops: list[ImageCrop],
    context: EmbeddingContext,
    show_progress: bool,
) -> EmbeddingResult:
    """Embed image crops, opening each source file once and skipping broken files.

    Crops are grouped by source filepath and each file is opened once. If a file is
    unreadable/undecodable, all of its crops are skipped rather than aborting the whole
    run; the file is recorded once as broken.

    Args:
        image_crops: Crop definitions to embed.
        context: Model-specific embedding configuration.
        show_progress: Whether to show a tqdm progress bar.

    Returns:
        An ``EmbeddingResult`` whose embeddings cover only the crops of readable
        files, with ``kept_indices`` mapping each row back to its input position.

    Raises:
        AllInputFilesFailedError: If at least one file was attempted and every attempted
            file was broken (i.e. no file could be read and embedded).
        ValueError: If ``context.max_batch_size`` is not positive.
    """
    total_crops = len(image_crops)
    if not total_crops:
        empty = np.empty((0, context.embedding_dimension), dtype=np.float32)
        return EmbeddingResult(embeddings=empty, kept_indices=[])

    if context.max_batch_size <= 0:
        raise ValueError("max_batch_size must be positive.")

    crops_by_filepath: dict[str, list[tuple[int, ImageCrop]]] = {}
    for index, image_crop in enumerate(image_crops):
        crops_by_filepath.setdefault(image_crop.filepath, []).append((index, image_crop))

    embeddings = np.empty((total_crops, context.embedding_dimension), dtype=np.float32)
    # Input indices of the crops that were embedded (their file could be read).
    kept_indices: list[int] = []
    # Reusable batch buffer, lazily sized from the first preprocessed crop.
    batch_buffer: torch.Tensor | None = None
    batch_indices: list[int] = []
    report = FileOutcomeReport()

    with (
        tqdm(
            total=total_crops,
            desc="Generating crop embeddings",
            unit=" crops",
            disable=not show_progress,
        ) as progress_bar,
        torch.no_grad(),
    ):
        source_image_crop_groups = (
            _SourceImageCrops(filepath=filepath, indexed_crops=indexed_crops)
            for filepath, indexed_crops in crops_by_filepath.items()
        )
        workers = executor.get_media_worker_count()
        loaded_source_images = parallelize.thread_imap_lazy(
            function=_load_source_image,
            iterable=source_image_crop_groups,
            max_workers=workers,
            buffer_size=workers,
        )
        for loaded_source_image_crops in loaded_source_images:
            image = loaded_source_image_crops.image
            if image is None:
                report.record(path=loaded_source_image_crops.filepath, outcome=FileOutcome.BROKEN)
                continue
            report.record(path=loaded_source_image_crops.filepath, outcome=FileOutcome.ADDED)
            try:
                for index, image_crop in loaded_source_image_crops.indexed_crops:
                    preprocessed = context.preprocess(
                        image.crop(
                            (
                                image_crop.x,
                                image_crop.y,
                                image_crop.x + image_crop.width,
                                image_crop.y + image_crop.height,
                            )
                        )
                    )
                    if batch_buffer is None:
                        batch_buffer = torch.empty(
                            (context.max_batch_size, *preprocessed.shape),
                            dtype=preprocessed.dtype,
                        )
                    batch_buffer[len(batch_indices)] = preprocessed
                    batch_indices.append(index)
                    kept_indices.append(index)
                    if len(batch_indices) >= context.max_batch_size:
                        _flush_crop_batch(
                            batch_buffer=batch_buffer,
                            batch_indices=batch_indices,
                            embeddings=embeddings,
                            context=context,
                            progress_bar=progress_bar,
                        )
            finally:
                image.close()

        _flush_crop_batch(
            batch_buffer=batch_buffer,
            batch_indices=batch_indices,
            embeddings=embeddings,
            context=context,
            progress_bar=progress_bar,
        )

    report.raise_if_all_failed()
    report.log_summary()

    # kept_indices in input order maps each returned row back to its input crop.
    kept_indices.sort()
    return EmbeddingResult(embeddings=embeddings[kept_indices], kept_indices=kept_indices)


def _load_source_image(
    source_image_crops: _SourceImageCrops,
) -> _LoadedSourceImageCrops:
    """Open and decode one source image in a worker thread."""
    filepath = source_image_crops.filepath
    try:
        with fsspec.open(filepath, "rb") as file, Image.open(file) as opened_image:
            image = opened_image.convert("RGB")
    except BROKEN_IMAGE_ERRORS:
        return _LoadedSourceImageCrops(
            filepath=filepath,
            indexed_crops=source_image_crops.indexed_crops,
            image=None,
        )
    return _LoadedSourceImageCrops(
        filepath=filepath,
        indexed_crops=source_image_crops.indexed_crops,
        image=image,
    )


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
