"""Structural protocols an embedder implements to declare its capabilities."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.capability import EmbedderDescriptor


@runtime_checkable
class Embedder(Protocol):
    """Base protocol shared by every embedder.

    <span class="doc-badge doc-badge--beta">Beta</span>

    An embedder identifies itself through ``load``. Implement one or more of the
    capability protocols below to declare what kinds of input it can embed.
    """

    def load(self) -> EmbedderDescriptor:
        """Realize the model and return its identity.

        <span class="doc-badge doc-badge--beta">Beta</span>

        The framework calls this once, before any embed call. The returned
        descriptor is authoritative and must not change afterwards. Put heavy
        setup work here (for example loading model weights) rather than in
        ``__init__`` so that constructing an embedder stays cheap.

        Returns:
            The descriptor with model id, dimension, and capabilities.
        """
        ...


@runtime_checkable
class TextEmbedder(Protocol):
    """Protocol for embedding text.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for text inputs.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Args:
            texts: The texts to embed.

        Returns:
            An ``EmbeddingResult`` with embeddings for the embedded texts, in input
            order. Use ``kept_indices`` to line the rows up with the input texts.
        """
        ...


@runtime_checkable
class ImagePathEmbedder(Protocol):
    """Protocol for embedding images referenced by ``fsspec`` path or URL.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Generate embeddings for images read from paths.

        <span class="doc-badge doc-badge--beta">Beta</span>

        Args:
            paths: ``fsspec``-compatible paths to the images to embed. Each one is an
                absolute local path (e.g. ``/data/cat.jpg``) or a remote URI
                (e.g. ``s3://bucket/cat.jpg``).

        Returns:
            An ``EmbeddingResult`` with embeddings for the readable images, in input
            order. Use ``kept_indices`` to skip images that could not be embedded.
        """
        ...
