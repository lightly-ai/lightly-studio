"""Registry that maps embedding spaces and capabilities to embedders.

Holds at most one embedder per ``(space_key, capability)`` pair. Callers look up
an embedder by the capability they need with the matching typed getter.
"""

from __future__ import annotations

import logging

from lightly_studio.embed.embedder import (
    Capability,
    CropPathEmbedder,
    Embedder,
    FramePILEmbedder,
    ImageBytesEmbedder,
    ImagePathEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.types import EmbeddingSpaceSpec

logger = logging.getLogger(__name__)

_CAPABILITY_TO_TYPE = {
    Capability.IMAGE_PATH: ImagePathEmbedder,
    Capability.CROP_PATH: CropPathEmbedder,
    Capability.VIDEO_PATH: VideoPathEmbedder,
    Capability.FRAME_PIL: FramePILEmbedder,
    Capability.TEXT: TextEmbedder,
    Capability.IMAGE_BYTES: ImageBytesEmbedder,
}


class EmbedderRegistry:
    """Stores embedders keyed by embedding space and capability.

    An embedder can provide several capabilities. For a given space, the registry
    stores at most one embedder per capability. Registering an embedder for the same
    space and capability replaces the old one.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._by_space_and_capability: dict[tuple[str, Capability], Embedder] = {}
        self._spec_by_space: dict[str, EmbeddingSpaceSpec] = {}

    def register(self, embedder: Embedder) -> None:
        """Register an embedder under every capability it implements.

        The capabilities are inferred from the embedder's type. The embedding
        space is read from ``embedder.embedding_space_spec()``.

        Args:
            embedder: The embedder to register.

        Raises:
            ValueError: If the embedder's embedding space shares a ``space_key``
                with an already registered space but does not match its spec, or
                if the embedder implements no capability.
        """
        spec = embedder.embedding_space_spec()
        space_key = spec.space_key
        capabilities = _capabilities_of(embedder=embedder)
        if not capabilities:
            raise ValueError(f"Embedder {type(embedder).__name__!r} implements no capability.")
        registered_spec = self._spec_by_space.get(space_key)
        if registered_spec is not None and registered_spec != spec:
            raise ValueError(
                f"Embedding space {space_key!r} is already registered as {registered_spec}, "
                f"cannot register the incompatible {spec}."
            )
        self._spec_by_space[space_key] = spec
        for capability in capabilities:
            key = (space_key, capability)
            if key in self._by_space_and_capability:
                logger.warning(
                    "Replacing embedder for space %r and capability %s.",
                    space_key,
                    capability.value,
                )
            self._by_space_and_capability[key] = embedder

    def get_image_path_embedder(self, space_key: str) -> ImagePathEmbedder | None:
        """Get the embedder that embeds images by path for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.IMAGE_PATH))
        assert embedder is None or isinstance(embedder, ImagePathEmbedder)
        return embedder

    def get_crop_path_embedder(self, space_key: str) -> CropPathEmbedder | None:
        """Get the embedder that embeds crops by path for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.CROP_PATH))
        assert embedder is None or isinstance(embedder, CropPathEmbedder)
        return embedder

    def get_video_path_embedder(self, space_key: str) -> VideoPathEmbedder | None:
        """Get the embedder that embeds videos by path for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.VIDEO_PATH))
        assert embedder is None or isinstance(embedder, VideoPathEmbedder)
        return embedder

    def get_frame_pil_embedder(self, space_key: str) -> FramePILEmbedder | None:
        """Get the embedder that embeds video frames for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.FRAME_PIL))
        assert embedder is None or isinstance(embedder, FramePILEmbedder)
        return embedder

    def get_text_embedder(self, space_key: str) -> TextEmbedder | None:
        """Get the embedder that embeds text for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.TEXT))
        assert embedder is None or isinstance(embedder, TextEmbedder)
        return embedder

    def get_image_bytes_embedder(self, space_key: str) -> ImageBytesEmbedder | None:
        """Get the embedder that embeds images by bytes for the space, if any."""
        embedder = self._by_space_and_capability.get((space_key, Capability.IMAGE_BYTES))
        assert embedder is None or isinstance(embedder, ImageBytesEmbedder)
        return embedder


def _capabilities_of(embedder: Embedder) -> list[Capability]:
    """List the capabilities an embedder implements, inferred from its type."""
    return [
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    ]
