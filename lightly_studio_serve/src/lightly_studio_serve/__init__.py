"""Serve your own embedding model to LightlyStudio over HTTP."""

from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop

__all__ = [
    "Capability",
    "Embedder",
    "EmbeddingResult",
    "EmbeddingSpaceSpec",
    "ImageBytesEmbedder",
    "ImageCrop",
    "ImageCropPathEmbedder",
    "ImagePILEmbedder",
    "ImagePathEmbedder",
    "TextEmbedder",
    "VideoPathEmbedder",
]
