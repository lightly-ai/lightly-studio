"""Capability-split embedder interfaces.

Defines one abstract subclass per input a model can embed: images and crops by
path, videos, PIL images, text, and images by bytes. A concrete model implements
only the capabilities it supports, and callers pick an embedder by the capability
they need.

``Embedder`` and the capabilities a remote model can serve over HTTP
(``TextEmbedder``, ``ImageBytesEmbedder``, ``VideoBytesEmbedder``) come from
``lightly-studio-embed`` and are re-exported here, so an embedder written against
that package is the same type as one written against this one. The capabilities
below it are local only: they take an fsspec path or a PIL image, neither of which
crosses the wire.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum

from lightly_studio_embed.embedder import (
    BaseEmbedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from PIL.Image import Image

from lightly_studio.embed.types import EmbeddingResult, ImageCrop

# The base class is named for its role in the customer-facing package; inside
# LightlyStudio it has always been `Embedder`, and that name is public API.
Embedder = BaseEmbedder

# TODO(Michal, 09/2026): `ImageBytesEmbedder` is currently unused in-process. The
# interactive path creates a temp file and uses `ImagePathEmbedder`.

__all__ = [
    "Capability",
    "Embedder",
    "ImageBytesEmbedder",
    "ImageCropPathEmbedder",
    "ImagePILEmbedder",
    "ImagePathEmbedder",
    "TextEmbedder",
    "VideoBytesEmbedder",
    "VideoPathEmbedder",
]


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
