"""Capability-split embedder interfaces.

Defines the ``Embedder`` base class and one abstract subclass per input a model
can embed: text, images by path or bytes, image crops by path or bytes, video
frames, and videos. A concrete model implements only the capabilities it
supports, and callers pick an embedder by the capability they need. The value
types passed and returned live in ``types``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from PIL.Image import Image

from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop


class Capability(str, Enum):
    """An input kind an embedder can turn into embeddings.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    TEXT = "text"
    IMAGE_PATH = "image_path"
    """Offline ingest: images referenced by fsspec path or URL."""

    IMAGE_BYTES = "image_bytes"
    """Online search: raw upload bytes, e.g. a drag-and-drop query image."""

    CROP_PATH = "crop_path"
    """Offline ingest: a crop given as an image path plus a pixel box."""

    CROP_BYTES = "crop_bytes"
    """Online edits: a cropped region shipped as bytes."""

    FRAME_PIL = "frame_pil"
    """A single video frame given as a PIL image."""

    VIDEO_PATH = "video_path"
    """Offline ingest: a video referenced by fsspec path or URL."""


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


class ImagePathEmbedder(Embedder):
    """Embeds images read from an fsspec path or URL (local, ``s3://``, ...).

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for offline ingest, where images are referenced by path.
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


class ImageBytesEmbedder(Embedder):
    """Embeds images passed as raw bytes.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for online search, where the uploaded image has no path to read.
    Accepts only preselected formats: JPEG, PNG and WebP.
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


class CropPathEmbedder(Embedder):
    """Embeds crops of stored images, each an image path plus a pixel box.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for offline ingest.
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


class CropBytesEmbedder(Embedder):
    """Embeds cropped regions passed as raw bytes.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for online annotation edits, where the cropped region has no path to
    read.
    """

    # TODO(Michal, 09/2026): Confirm this is needed; ImageBytesEmbedder may cover it.

    __slots__ = ()

    @abstractmethod
    def embed_crop_bytes(self, crops: list[bytes]) -> EmbeddingResult:
        """Embed a batch of cropped regions given as encoded bytes.

        Args:
            crops: Encoded bytes of the cropped regions.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class FramePilEmbedder(Embedder):
    """Embeds video frames given as PIL images.

    <span class="doc-badge doc-badge--beta">Beta</span>
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


class VideoPathEmbedder(Embedder):
    """Embeds videos read from an fsspec path or URL.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Used for offline ingest.
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
