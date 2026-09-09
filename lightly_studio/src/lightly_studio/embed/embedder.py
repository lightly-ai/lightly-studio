"""Capability-split embedder interfaces.

Defines the ``Embedder`` base class and one abstract subclass per input a model
can embed: images and crops by path, videos, PIL images, text, and images by
bytes. A concrete model implements only the capabilities it supports, and
callers pick an embedder by the capability they need.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from PIL.Image import Image

from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop


class Capability(str, Enum):
    """An input kind an embedder can turn into embeddings.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Some capabilities are used at ingest, when data is loaded into the database.
    Others are needed interactively while the GUI runs.
    """

    IMAGE_PATH = "image_path"
    """Ingest: image by fsspec path."""

    IMAGE_CROP_PATH = "image_crop_path"
    """Ingest: crop specified by an image fsspec path and a pixel box."""

    VIDEO_PATH = "video_path"
    """Ingest: video by fsspec path."""

    IMAGE_PIL = "image_pil"
    """Ingest: image represented as a PIL image."""

    TEXT = "text"
    """Interactive: text query."""

    IMAGE_BYTES = "image_bytes"
    """Interactive and ingest: image as raw file bytes."""

    VIDEO_BYTES = "video_bytes"
    """Ingest: video as raw file bytes. No local implementation yet."""


class Embedder(ABC):
    """Base class for every embedder.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Subclasses add one abstract method per input they support. A concrete model
    implements the subclasses for the capabilities it provides.
    """

    __slots__ = ()

    @abstractmethod
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the embedding space this embedder produces.

        Returns:
            Metadata identifying the embedding space, stored so the same space
            can be recognized across LightlyStudio runs.
        """


class ImagePathEmbedder(Embedder):
    """Embeds images read from an fsspec path (local, ``s3://``, ...).

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed a batch of images given by path.

        Args:
            paths: fsspec paths of the images to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImageCropPathEmbedder(Embedder):
    """Embeds crops of stored images, each an image path plus a pixel box.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed a batch of image crops given by path and pixel box.

        Args:
            crops: The crops to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class VideoPathEmbedder(Embedder):
    """Embeds videos read from an fsspec path.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        """Embed a batch of videos given by path.

        Args:
            paths: fsspec paths of the videos to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImagePILEmbedder(Embedder):
    """Embeds images represented as PIL images.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_images_pil(self, images: list[Image]) -> EmbeddingResult:
        """Embed a batch of PIL images.

        Args:
            images: The PIL images to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class TextEmbedder(Embedder):
    """Embeds text queries.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed a batch of text strings.

        Args:
            texts: The strings to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImageBytesEmbedder(Embedder):
    """Embeds images passed as raw bytes.

    <span class="doc-badge doc-badge--beta">Beta</span>

    For callers that have no path to read, such as an upload. JPEG, PNG and
    WebP only.
    """

    __slots__ = ()

    @abstractmethod
    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Embed a batch of images given as encoded bytes.

        Args:
            images: Encoded image bytes (JPEG, PNG or WebP).

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        # TODO(Michal, 09/2026): Currently unused. The interactive path creates a temp
        # file and uses ImagePathEmbedder.
