"""Registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key``. Callers look up an embedder by the
capability they need with the matching typed getter, which returns the space's
embedder only when it implements that capability.
"""

from __future__ import annotations

import logging

from lightly_studio.embed.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)

logger = logging.getLogger(__name__)

_CAPABILITY_TO_TYPE = {
    Capability.IMAGE_PATH: ImagePathEmbedder,
    Capability.IMAGE_CROP_PATH: ImageCropPathEmbedder,
    Capability.VIDEO_PATH: VideoPathEmbedder,
    Capability.IMAGE_PIL: ImagePILEmbedder,
    Capability.TEXT: TextEmbedder,
    Capability.IMAGE_BYTES: ImageBytesEmbedder,
}


class EmbedderRegistry:
    """Stores at most one embedder per embedding space.

    An embedder can provide several capabilities. The registry keeps one embedder
    per ``space_key``; registering another embedder for the same space replaces
    it. The typed getters return the space's embedder only when it implements the
    requested capability.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._space_key_to_embedder: dict[str, Embedder] = {}

    def register(self, embedder: Embedder) -> None:
        """Register an embedder for its embedding space.

        The embedding space is read from ``embedder.embedding_space_spec()``. If an
        embedder is already registered for the same space, it is replaced.

        Args:
            embedder: The embedder to register.

        Raises:
            ValueError: If the embedder implements no capability, or if it shares
                a ``space_key`` with an already registered embedder but does not
                match its spec.
        """
        spec = embedder.embedding_space_spec()
        space_key = spec.space_key
        if not _capabilities_of(embedder=embedder):
            raise ValueError(f"Embedder {type(embedder).__name__!r} implements no capability.")
        registered = self._space_key_to_embedder.get(space_key)
        if registered is not None:
            registered_spec = registered.embedding_space_spec()
            if registered_spec != spec:
                raise ValueError(
                    f"Embedding space {space_key!r} is already registered as {registered_spec}, "
                    f"cannot register the incompatible {spec}."
                )
            logger.warning("Replacing embedder for space %r.", space_key)
        self._space_key_to_embedder[space_key] = embedder

    def get_image_path_embedder(self, space_key: str) -> ImagePathEmbedder | None:
        """Get the space's embedder if it embeds images by path, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, ImagePathEmbedder) else None

    def get_image_crop_path_embedder(self, space_key: str) -> ImageCropPathEmbedder | None:
        """Get the space's embedder if it embeds crops by path, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, ImageCropPathEmbedder) else None

    def get_video_path_embedder(self, space_key: str) -> VideoPathEmbedder | None:
        """Get the space's embedder if it embeds videos by path, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, VideoPathEmbedder) else None

    def get_image_pil_embedder(self, space_key: str) -> ImagePILEmbedder | None:
        """Get the space's embedder if it embeds PIL images, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, ImagePILEmbedder) else None

    def get_text_embedder(self, space_key: str) -> TextEmbedder | None:
        """Get the space's embedder if it embeds text, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, TextEmbedder) else None

    def get_image_bytes_embedder(self, space_key: str) -> ImageBytesEmbedder | None:
        """Get the space's embedder if it embeds images by bytes, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, ImageBytesEmbedder) else None


def _capabilities_of(embedder: Embedder) -> list[Capability]:
    """List the capabilities an embedder implements, inferred from its type."""
    return [
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    ]
