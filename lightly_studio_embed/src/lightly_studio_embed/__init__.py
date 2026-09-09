"""Serve your own embedding model to LightlyStudio over HTTP."""

from lightly_studio_embed.embedder import (
    BaseEmbedder,
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import CapabilityNotImplementedError, EmbedderContractError
from lightly_studio_embed.protocol import (
    PROTOCOL_VERSION,
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    EmbedUrlsRequest,
    ServerLimits,
    WireCapability,
)
from lightly_studio_embed.server import create_app, serve

__all__ = [
    "PROTOCOL_VERSION",
    "BaseEmbedder",
    "CapabilityNotImplementedError",
    "DescribeResponse",
    "EmbedTextsRequest",
    "EmbedUrlsRequest",
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
