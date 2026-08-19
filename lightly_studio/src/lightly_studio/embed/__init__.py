"""Embedder protocols, base class, registry, and manager.

Public re-exports for the embedding prototype. ``EmbeddingResult`` is re-exported
from ``lightly_studio.dataset.embedding_result`` so the whole embedder surface is
importable from this package.
"""

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder
from lightly_studio.embed.capability import Capability, EmbedderDescriptor
from lightly_studio.embed.manager import register_default_embedder
from lightly_studio.embed.protocols import Embedder, ImagePathEmbedder, TextEmbedder
from lightly_studio.embed.random_embedder import RandomEmbedder

__all__ = [
    "BaseEmbedder",
    "Capability",
    "Embedder",
    "EmbedderDescriptor",
    "EmbeddingResult",
    "ImagePathEmbedder",
    "RandomEmbedder",
    "TextEmbedder",
    "register_default_embedder",
]
