"""Serve your own embedding model to LightlyStudio over HTTP."""

from lightly_studio_embed.embedder import (
    BaseEmbedder,
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.protocol import (
    PROTOCOL_VERSION,
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
    WireCapability,
)
from lightly_studio_embed.server import create_app, serve
from lightly_studio_embed.validation import EmbedderContractError

__all__ = [
    "PROTOCOL_VERSION",
    "BaseEmbedder",
    "DescribeResponse",
    "EmbedTextsRequest",
    "EmbedderContractError",
    "EmbeddingResult",
    "EmbeddingsResponse",
    "ImageBytesEmbedder",
    "ServerLimits",
    "TextEmbedder",
    "VideoBytesEmbedder",
    "WireCapability",
    "create_app",
    "serve",
]
