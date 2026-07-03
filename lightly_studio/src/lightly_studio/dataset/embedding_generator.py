"""EmbeddingGenerator implementations."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from lightly_studio.models.embedding_model import EmbeddingModelCreate


@dataclass(frozen=True)
class ImageCrop:
    """Image crop to embed."""

    filepath: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class BatchedEmbeddingResult:
    """Embeddings for the successfully embedded inputs, keyed by sample id.

    Broken inputs are skipped per-item instead of aborting the batch, so this
    may cover fewer inputs than were passed. ``keys[i]`` is the sample id of the
    input that produced ``embeddings[i]`` — the id travels with the data through
    batching and skipping, so callers never re-align by position.

    Attributes:
        embeddings: Float32 array of shape ``(len(keys), dimension)``.
        keys: Sample id for each embedding row, in row order.
    """

    embeddings: NDArray[np.float32]
    keys: list[UUID]


@runtime_checkable
class EmbeddingGenerator(Protocol):
    """Protocol defining the interface for embedding models.

    This protocol defines the interface that all embedding models must
    implement. Concrete implementations will use different techniques
    for creating embeddings.
    """

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            collection_id: The ID of the collection.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a text sample.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        ...


@runtime_checkable
class ImageEmbeddingGenerator(EmbeddingGenerator, Protocol):
    """Protocol defining the interface for image embedding models.

    This protocol defines the interface that all image embedding models must
    implement. Concrete implementations will use different techniques
    for creating embeddings.
    """

    def embed_images(
        self,
        keyed_filepaths: Sequence[tuple[UUID, str]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Generate embeddings for multiple image samples.

        TODO(Michal, 04/2025): Use DatasetLoader as input instead.

        Each embedding is tagged with the sample id paired with its filepath, so
        callers map results back by identity rather than by position.

        Args:
            keyed_filepaths: ``(sample_id, filepath)`` pairs to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            Embeddings for the embedded inputs, keyed by sample id.
        """
        ...

    def embed_image_crops(
        self,
        keyed_crops: Sequence[tuple[UUID, ImageCrop]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Generate embeddings for image crops.

        Each embedding is tagged with the sample id paired with its crop, so
        callers map results back by identity rather than by position.

        Args:
            keyed_crops: ``(sample_id, crop)`` pairs to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            Embeddings for the embedded crops, keyed by sample id.
        """
        ...


@runtime_checkable
class VideoEmbeddingGenerator(EmbeddingGenerator, Protocol):
    """Protocol defining the interface for video embedding models.

    This protocol defines the interface that all video embedding models must
    implement. Concrete implementations will use different techniques
    for creating embeddings.
    """

    def embed_videos(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Generate embeddings for multiple video samples.

        Args:
            filepaths: A list of file paths to the videos to embed.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        ...


class RandomEmbeddingGenerator(ImageEmbeddingGenerator, VideoEmbeddingGenerator):
    """Model that produces random embeddings with a fixed dimension."""

    def __init__(self, dimension: int = 3):
        """Initialize the random embedding model.

        Args:
            dimension: The dimension of the embedding vectors to generate.
        """
        self._dimension = dimension

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            collection_id: The ID of the collection.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name="Random",
            embedding_model_hash="random_model",
            embedding_dimension=self._dimension,
            collection_id=collection_id,
        )

    def embed_text(self, _text: str) -> list[float]:
        """Generate a random embedding for a text sample."""
        return [random.random() for _ in range(self._dimension)]

    def embed_images(
        self,
        keyed_filepaths: Sequence[tuple[UUID, str]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Generate random embeddings for multiple image samples."""
        _ = show_progress  # Not used for random embeddings.
        keys = [key for key, _ in keyed_filepaths]
        embeddings = np.random.rand(len(keys), self._dimension).astype(np.float32)
        return BatchedEmbeddingResult(embeddings=embeddings, keys=keys)

    def embed_image_crops(
        self,
        keyed_crops: Sequence[tuple[UUID, ImageCrop]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Generate random embeddings for multiple image crops."""
        _ = show_progress  # Not used for random embeddings.
        keys = [key for key, _ in keyed_crops]
        embeddings = np.random.rand(len(keys), self._dimension).astype(np.float32)
        return BatchedEmbeddingResult(embeddings=embeddings, keys=keys)

    def embed_videos(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Generate random embeddings for multiple video samples."""
        return np.random.rand(len(filepaths), self._dimension).astype(np.float32)
