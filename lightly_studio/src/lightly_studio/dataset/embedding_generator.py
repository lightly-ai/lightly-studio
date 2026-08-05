"""EmbeddingGenerator implementations."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.models.embedding_model import EmbeddingModelCreate


@dataclass(frozen=True)
class ImageCrop:
    """A rectangular region of an image to embed, given in pixel coordinates."""

    filepath: str
    """Path to the image the crop is taken from."""

    x: int
    """Left edge of the crop, in pixels from the image's left."""

    y: int
    """Top edge of the crop, in pixels from the image's top."""

    width: int
    """Crop width in pixels."""

    height: int
    """Crop height in pixels."""


@runtime_checkable
class EmbeddingGenerator(Protocol):
    """Base protocol shared by every embedding generator.

    A generator supplies the model metadata LightlyStudio stores per collection
    (``get_embedding_model_input``) and embeds text queries (``embed_text``), which
    powers text-based similarity search. Implement one of the more specific protocols
    below (``ImageEmbeddingGenerator`` and/or ``VideoEmbeddingGenerator``) to embed
    images or videos, then register it with ``set_default_embedding_model`` before
    ingesting a dataset.
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
    """Protocol for embedding images, image crops, and text.

    Implement this to plug your own image model into LightlyStudio, either by running
    the model on the given file paths or by looking up precomputed vectors. A registered
    image generator overrides image, annotation-crop, and text embeddings. It inherits
    ``embed_text`` from ``EmbeddingGenerator``, so keep the text and image encoders
    in the same space for text-based image search to work.
    """

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Generate embeddings for multiple image samples.

        Args:
            filepaths: A list of file paths to the images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            An ``EmbeddingResult`` with embeddings for the readable files, in the same
            order as the corresponding input file paths. Use ``kept_indices`` to skip
            any file paths you cannot or do not want to embed.
        """
        ...

    def embed_image_crops(
        self, image_crops: list[ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Generate embeddings for image crops.

        Args:
            image_crops: A list of image crop definitions to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            An ``EmbeddingResult`` with embeddings for the crops of readable files,
            in the same order as the corresponding input crops.
        """
        ...

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Generate embeddings for in-memory PIL images.

        Args:
            images: PIL images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings in the same order
            as the input images.
        """
        ...


@runtime_checkable
class VideoEmbeddingGenerator(EmbeddingGenerator, Protocol):
    """Protocol for embedding videos (and text).

    Implement this to plug your own video model into LightlyStudio. A registered video
    generator overrides video and text embeddings. It inherits ``embed_text`` from
    ``EmbeddingGenerator``; keep the text and video encoders in the same space for
    text-based video search to work. Implement it alongside ``ImageEmbeddingGenerator``
    on the same object to override both image and video.
    """

    def embed_videos(self, filepaths: list[str]) -> EmbeddingResult:
        """Generate embeddings for multiple video samples.

        Args:
            filepaths: A list of file paths to the videos to embed.

        Returns:
            An ``EmbeddingResult`` with embeddings for the readable videos, in the same
            order as the corresponding input file paths.
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

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Generate random embeddings for multiple image samples."""
        _ = show_progress  # Not used for random embeddings.
        embeddings = np.random.rand(len(filepaths), self._dimension).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(filepaths))))

    def embed_image_crops(
        self, image_crops: list[ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Generate random embeddings for multiple image crops."""
        _ = show_progress  # Not used for random embeddings.
        embeddings = np.random.rand(len(image_crops), self._dimension).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(image_crops))))

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Generate random embeddings for in-memory PIL images."""
        _ = show_progress  # Not used for random embeddings.
        return np.random.rand(len(images), self._dimension).astype(np.float32)

    def embed_videos(self, filepaths: list[str]) -> EmbeddingResult:
        """Generate random embeddings for multiple video samples."""
        embeddings = np.random.rand(len(filepaths), self._dimension).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(filepaths))))
