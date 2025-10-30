"""EmbeddingGenerator implementations."""

from __future__ import annotations

import random
from typing import Protocol, runtime_checkable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from lightly_studio.models.embedding_model import EmbeddingModelCreate


@runtime_checkable
class EmbeddingGenerator(Protocol):
    """Protocol defining the interface for embedding models.

    This protocol defines the interface that all embedding models must
    implement. Concrete implementations will use different techniques
    for creating embeddings.
    """

    def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            dataset_id: The ID of the dataset.

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

    def embed_images(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Generate embeddings for multiple image samples.

        TODO(Michal, 04/2025): Use DatasetLoader as input instead.

        Args:
            filepaths: A list of file paths to the images to embed.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        ...


class RandomEmbeddingGenerator(EmbeddingGenerator):
    """Model that produces random embeddings with a fixed dimension."""

    def __init__(self, dimension: int = 3):
        """Initialize the random embedding model.

        Args:
            dimension: The dimension of the embedding vectors to generate.
        """
        self._dimension = dimension

    def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            dataset_id: The ID of the dataset.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name="Random",
            embedding_model_hash="random_model",
            embedding_dimension=self._dimension,
            dataset_id=dataset_id,
        )

    def embed_text(self, _text: str) -> list[float]:
        """Generate a random embedding for a text sample."""
        return [random.random() for _ in range(self._dimension)]

    def embed_images(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Generate random embeddings for multiple image samples."""
        return np.random.rand(len(filepaths), self._dimension).astype(np.float32)
