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
    """A rectangular region of an image to embed, given in pixel coordinates.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

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

    <span class="doc-badge doc-badge--beta">Beta</span>

    An EmbeddingGenerator provides embeddings for images, image crops, videos, video frames
    or other sample types. Every sample collection can have a different associated embedding
    generator. The generator is used at two points:

    - During data loading to compute sample embeddings
    - During a GUI run to embed text or image search queries

    Generators are loaded at startup and need to identify themselves with
    `get_embedding_model_input` which returns metadata about the loaded model.

    To provide custom embeddings, implement one of the protocols below (``ImageEmbeddingGenerator``
    and/or ``VideoEmbeddingGenerator``) and register it with ``set_default_embedding_model``
    before you add a dataset or start the GUI.
    """

    def get_embedding_model_input(
        self, collection_id: UUID, dataset_id: UUID
    ) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Returns metadata about the model to be stored in the database.
        The `embedding_model_hash` field is used to match the same EmbeddingGenerator
        across multiple LightlyStudio runs.

        Args:
            collection_id: The ID of the collection.
            dataset_id: The ID of the dataset.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a text sample.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        ...


@runtime_checkable
class ImageEmbeddingGenerator(EmbeddingGenerator, Protocol):
    """Protocol for embedding images, image crops, and text.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Implement this to use your own image model in LightlyStudio. Inside ``embed_images``
    you can run the model on the given file paths or look up precomputed vectors. A
    registered image generator replaces the built-in image, crop, and text embeddings.
    It inherits ``embed_text`` from ``EmbeddingGenerator``, so keep the text and image
    encoders in the same embedding space for text-based image and crop search to work.
    """

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Generate embeddings for multiple image samples.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Args:
            filepaths: A list of ``fsspec``-compatible file paths to the images to embed.
                Each one is an absolute local path with forward slashes (e.g. ``/data/cat.jpg``)
                or a remote URI (e.g. ``s3://bucket/cat.jpg``).
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

        <span class="doc-badge doc-badge--beta">Beta</span>

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

        <span class="doc-badge doc-badge--beta">Beta</span>

        Used for video frame embedding.

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

    <span class="doc-badge doc-badge--beta">Beta</span>

    Implement this to use your own video model in LightlyStudio. A registered video
    generator replaces the built-in video and text embeddings. It inherits ``embed_text``
    from ``EmbeddingGenerator``, so keep the text and video encoders in the same embedding
    space for text-based video search to work.
    """

    def embed_videos(self, filepaths: list[str]) -> EmbeddingResult:
        """Generate embeddings for multiple video samples.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Args:
            filepaths: A list of ``fsspec``-compatible file paths to the videos to embed.
                Each one is an absolute local path with forward slashes (e.g. ``/data/clip.mp4``)
                or a remote URI (e.g. ``s3://bucket/clip.mp4``).

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

    def get_embedding_model_input(
        self, collection_id: UUID, dataset_id: UUID
    ) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            collection_id: The ID of the collection.
            dataset_id: The ID of the dataset.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name="Random",
            embedding_model_hash="random_model",
            embedding_dimension=self._dimension,
            collection_id=collection_id,
            dataset_id=dataset_id,
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
