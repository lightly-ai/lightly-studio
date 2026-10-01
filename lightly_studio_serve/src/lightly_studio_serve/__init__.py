"""Serve your own embedding model to LightlyStudio over HTTP."""

from lightly_studio_serve.embedder import (
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
from lightly_studio_serve.server import create_app, serve
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
    "VideoBytesEmbedder",
    "VideoPathEmbedder",
    "create_app",
    "serve",
]
