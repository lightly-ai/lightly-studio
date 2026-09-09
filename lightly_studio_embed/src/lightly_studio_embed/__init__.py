"""Serve your own embedding model to LightlyStudio over HTTP."""

from lightly_studio_embed.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
    VideoPathEmbedder,
)
from lightly_studio_embed.server import create_app
from lightly_studio_embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop

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
    "VideoBytesEmbedder",
    "VideoPathEmbedder",
    "create_app",
]
