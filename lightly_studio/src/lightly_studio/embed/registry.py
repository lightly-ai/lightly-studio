"""Registry that stores one embedder per capability with typed lookup."""

from __future__ import annotations

from lightly_studio.embed.capability import Capability
from lightly_studio.embed.protocols import Embedder, ImagePathEmbedder, TextEmbedder


class EmbedderRegistry:
    """Holds the default embedder for each capability.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Each capability has its own typed slot so lookups return a concrete protocol
    type rather than a generic ``Embedder``.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._text_embedder: TextEmbedder | None = None
        self._image_path_embedder: ImagePathEmbedder | None = None

    def register(self, embedder: Embedder) -> None:
        """Register an embedder into the slots for each capability it offers.

        Args:
            embedder: The embedder to register. Its capabilities determine which
                slots it fills.
        """
        capabilities = embedder.describe().capabilities
        if Capability.TEXT in capabilities:
            # The capability set was derived from these very protocols.
            assert isinstance(embedder, TextEmbedder)
            self._text_embedder = embedder
        if Capability.IMAGE_PATH in capabilities:
            assert isinstance(embedder, ImagePathEmbedder)
            self._image_path_embedder = embedder

    def get_default_text_embedder(self) -> TextEmbedder | None:
        """Return the registered text embedder, or None if none is registered."""
        return self._text_embedder

    def get_default_image_path_embedder(self) -> ImagePathEmbedder | None:
        """Return the registered image-path embedder, or None if none is registered."""
        return self._image_path_embedder
