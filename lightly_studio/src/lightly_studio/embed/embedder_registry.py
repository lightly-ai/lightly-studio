"""Process-wide registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key`` and the built-in bootstrap defaults.
Callers look up an embedder by the capability they need with the matching typed
getter, which returns the space's embedder only when it implements that capability.
The registry never touches the database; persisting a collection's default space is
the caller's responsibility.
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
from lightly_studio.embed.types import EmbeddingSpaceSpec

logger = logging.getLogger(__name__)

# Capabilities that have no local implementation yet are absent.
_CAPABILITY_TO_TYPE = {
    Capability.IMAGE_PATH: ImagePathEmbedder,
    Capability.IMAGE_CROP_PATH: ImageCropPathEmbedder,
    Capability.VIDEO_PATH: VideoPathEmbedder,
    Capability.IMAGE_PIL: ImagePILEmbedder,
    Capability.TEXT: TextEmbedder,
    Capability.IMAGE_BYTES: ImageBytesEmbedder,
}
# Capabilities whose bootstrap default is produced by an offline built-in embedder,
# each mapped to the space_key used to bootstrap a collection default.
_DEFAULT_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = {
    Capability.IMAGE_PATH: "mobileclip_s0",
    Capability.IMAGE_CROP_PATH: "mobileclip_s0",
    Capability.IMAGE_PIL: "mobileclip_s0",
    Capability.VIDEO_PATH: "PE-Core-T16-384",
}
_OFFLINE_CAPABILITIES = frozenset(_DEFAULT_BOOTSTRAP_SPACE_KEYS)


class EmbedderRegistry:
    """Stores at most one embedder per embedding space and the bootstrap defaults.

    An embedder can provide several capabilities. The registry keeps one embedder
    per ``space_key``; registering another embedder for the same space replaces it.
    Each capability maps to the ``space_key`` used to bootstrap a collection default
    when none is saved yet. The typed getters return the space's embedder only when
    it implements the requested capability, loading a built-in embedder on demand.
    """

    def __init__(self) -> None:
        """Create a registry seeded with the built-in bootstrap defaults."""
        self._space_key_to_embedder: dict[str, Embedder] = {}
        self._bootstrap_space_keys: dict[Capability, str] = dict(_DEFAULT_BOOTSTRAP_SPACE_KEYS)

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

    def register_embedder(self, embedder: Embedder) -> None:
        """Register a runtime provider and make it the offline bootstrap default.

        The embedder becomes the bootstrap default for every offline capability it
        implements, replacing any previous default for those capabilities.
        """
        self.register(embedder=embedder)
        space_key = embedder.embedding_space_spec().space_key
        for capability in set(_capabilities_of(embedder=embedder)) & _OFFLINE_CAPABILITIES:
            self._bootstrap_space_keys[capability] = space_key

    def bootstrap_space(self, capability: Capability) -> EmbeddingSpaceSpec | None:
        """Get the built-in embedding space to bootstrap for a capability, if available."""
        embedder = self._get_or_bootstrap(space_key=None, capability=capability)
        if embedder is None or capability not in _capabilities_of(embedder=embedder):
            return None
        return embedder.embedding_space_spec()

    def get_image_path_embedder(self, space_key: str | None = None) -> ImagePathEmbedder | None:
        """Get the space's image-path embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_PATH)
        return embedder if isinstance(embedder, ImagePathEmbedder) else None

    def get_image_crop_path_embedder(
        self, space_key: str | None = None
    ) -> ImageCropPathEmbedder | None:
        """Get the space's image-crop embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(
            space_key=space_key, capability=Capability.IMAGE_CROP_PATH
        )
        return embedder if isinstance(embedder, ImageCropPathEmbedder) else None

    def get_video_path_embedder(self, space_key: str | None = None) -> VideoPathEmbedder | None:
        """Get the space's video-path embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.VIDEO_PATH)
        return embedder if isinstance(embedder, VideoPathEmbedder) else None

    def get_image_pil_embedder(self, space_key: str | None = None) -> ImagePILEmbedder | None:
        """Get the space's PIL-image embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_PIL)
        return embedder if isinstance(embedder, ImagePILEmbedder) else None

    def get_text_embedder(self, space_key: str | None = None) -> TextEmbedder | None:
        """Get the space's text embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.TEXT)
        return embedder if isinstance(embedder, TextEmbedder) else None

    def get_image_bytes_embedder(self, space_key: str | None = None) -> ImageBytesEmbedder | None:
        """Get the space's image-bytes embedder, or the bootstrap default when space_key is None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_BYTES)
        return embedder if isinstance(embedder, ImageBytesEmbedder) else None

    def _get_or_bootstrap(self, space_key: str | None, capability: Capability) -> Embedder | None:
        """Resolve the space's embedder, falling back to the capability's bootstrap default."""
        if space_key is None:
            space_key = self._bootstrap_space_keys.get(capability)
        if space_key is None:
            return None
        return self._get_or_load(space_key=space_key)

    def _get_or_load(self, space_key: str) -> Embedder | None:
        registered = self._space_key_to_embedder.get(space_key)
        if registered is not None:
            return registered
        embedder = _load_builtin_embedder(space_key=space_key)
        if embedder is None:
            return None
        self.register(embedder=embedder)
        return embedder


# Process-wide registry shared by the app and by callers that look up embedders.
registry = EmbedderRegistry()


def _capabilities_of(embedder: Embedder) -> list[Capability]:
    """List the capabilities an embedder implements, inferred from its type."""
    return [
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    ]


def _load_builtin_embedder(space_key: str) -> Embedder | None:
    """Construct the built-in embedder for a space key, or None if there is none."""
    if space_key == "mobileclip_s0":
        from lightly_studio.embed.mobileclip_embedder import MobileCLIPEmbedder  # noqa: PLC0415

        return MobileCLIPEmbedder()
    if space_key == "PE-Core-T16-384":
        from lightly_studio.embed.perception_encoder_embedder import (  # noqa: PLC0415
            PerceptionEncoderEmbedder,
        )

        return PerceptionEncoderEmbedder()
    return None
