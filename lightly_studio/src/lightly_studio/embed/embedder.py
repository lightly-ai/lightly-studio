"""Capability-split embedder interfaces.

Defines the ``Embedder`` base class and one abstract subclass per input a model
can embed: images and crops by path, videos, video frames, text, and images by
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
    """Ingest: image by fsspec path or URL."""

    IMAGE_CROP_PATH = "image_crop_path"
    """Ingest: crop specified by an image fsspec or URL and a pixel box."""

    VIDEO_PATH = "video_path"
    """Ingest: video by fsspec path or URL."""

    IMAGE_PIL = "image_pil"
    """Ingest: video frame as a PIL image."""

    TEXT = "text"
    """Interactive: text query."""

    IMAGE_BYTES = "image_bytes"
    """Interactive: image as raw file bytes."""


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
    """Embeds images read from an fsspec path or URL (local, ``s3://``, ...).

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used at ingest.
    """

    __slots__ = ()

    @abstractmethod
    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed a batch of images given by path.

        Args:
            paths: fsspec paths or URLs of the images to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImageCropPathEmbedder(Embedder):
    """Embeds crops of stored images, each an image path plus a pixel box.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used at ingest.
    """

    __slots__ = ()

    @abstractmethod
    def embed_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed a batch of image crops given by path and pixel box.

        Args:
            crops: The crops to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class VideoPathEmbedder(Embedder):
    """Embeds videos read from an fsspec path or URL.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used at ingest.
    """

    __slots__ = ()

    @abstractmethod
    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        """Embed a batch of videos given by path.

        Args:
            paths: fsspec paths or URLs of the videos to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImagePILEmbedder(Embedder):
    """Embeds video frames given as PIL images.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used at ingest.
    """

    __slots__ = ()

    @abstractmethod
    def embed_frames(self, frames: list[Image]) -> EmbeddingResult:
        """Embed a batch of video frames.

        Args:
            frames: The frames to embed, as PIL images.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class TextEmbedder(Embedder):
    """Embeds text queries.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for interactive requests.
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

    Used for interactive requests, where the upload has no path to read. JPEG,
    PNG and WebP only.
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
