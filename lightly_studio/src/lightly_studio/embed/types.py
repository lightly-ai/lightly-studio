"""Shared value types for the embedding paths.

Holds the model-agnostic types passed to and returned by embedders:
``EmbeddingSpaceSpec``, ``EmbeddingResult`` and ``ImageCrop``. They live in their
own module so any caller can depend on them without importing the ``Embedder``
classes.

``EmbeddingSpaceSpec`` and ``EmbeddingResult`` are imported from
``lightly-studio-embed`` and re-exported here: a customer serving their own model
implements the same two types, so one definition keeps the two sides comparable.
``ImageCrop`` stays local, as an fsspec path is resolved with LightlyStudio's
credentials and so never crosses the wire.
"""

from __future__ import annotations

from dataclasses import dataclass

from lightly_studio_embed.types import EmbeddingResult, EmbeddingSpaceSpec

__all__ = ["EmbeddingResult", "EmbeddingSpaceSpec", "ImageCrop"]


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
