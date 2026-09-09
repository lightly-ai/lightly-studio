"""Process-wide registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key`` and the built-in bootstrap defaults.
Callers look up an embedder by the capability they need with the matching typed
getter, which returns the space's embedder only when it implements that capability.
The registry never touches the database; persisting a collection's default space is
the caller's responsibility.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

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
# Capabilities whose bootstrap default can be produced by an offline built-in embedder.
_OFFLINE_CAPABILITIES = frozenset(
    {
        Capability.IMAGE_PATH,
        Capability.IMAGE_CROP_PATH,
        Capability.VIDEO_PATH,
        Capability.IMAGE_PIL,
    }
)
_DEFAULT_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = {
    Capability.IMAGE_PATH: "mobileclip_s0",
    Capability.IMAGE_CROP_PATH: "mobileclip_s0",
    Capability.IMAGE_PIL: "mobileclip_s0",
    Capability.VIDEO_PATH: "PE-Core-T16-384",
}


class EmbedderRegistry:
    """Stores at most one embedder per embedding space.

    An embedder can provide several capabilities. The registry keeps one embedder
    per ``space_key``; registering another embedder for the same space replaces it.
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
        if not capabilities_of(embedder=embedder):
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

    def get(self, space_key: str) -> Embedder | None:
        """Get the registered provider for a space, regardless of capability."""
        return self._space_key_to_embedder.get(space_key)

    def clear(self) -> None:
        """Remove all registered embedders."""
        self._space_key_to_embedder.clear()

    def get_image_path_embedder(self, space_key: str) -> ImagePathEmbedder | None:
        """Get the space's embedder if it embeds images by path, else None."""
        embedder = self._space_key_to_embedder.get(space_key)
        return embedder if isinstance(embedder, ImagePathEmbedder) else None

    def get_image_crop_path_embedder(self, space_key: str) -> ImageCropPathEmbedder | None:
        """Get the space's embedder if it embeds image crops by path, else None."""
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


# Process-wide registry shared by the app and by callers that look up embedders.
_registry = EmbedderRegistry()
# Bootstrap default space per capability, seeded from the built-ins and updated by
# ``register_embedder``.
_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = dict(_DEFAULT_BOOTSTRAP_SPACE_KEYS)


def capabilities_of(embedder: Embedder) -> list[Capability]:
    """List the capabilities an embedder implements, inferred from its type."""
    return [
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    ]


def register_embedder(embedder: Embedder, default_for: Iterable[Capability] | None = None) -> None:
    """Register a runtime provider and optionally select offline bootstrap defaults."""
    capabilities = set(capabilities_of(embedder=embedder))
    selected = capabilities & _OFFLINE_CAPABILITIES if default_for is None else set(default_for)
    invalid = selected - capabilities
    if invalid:
        raise ValueError(
            f"Embedder does not implement capabilities: {_format_capabilities(invalid)}."
        )
    online = selected - _OFFLINE_CAPABILITIES
    if online:
        raise ValueError(f"Capabilities cannot bootstrap: {_format_capabilities(online)}.")

    _registry.register(embedder=embedder)
    space_key = embedder.embedding_space_spec().space_key
    for capability in selected:
        _BOOTSTRAP_SPACE_KEYS[capability] = space_key


def bootstrap_space(capability: Capability) -> EmbeddingSpaceSpec | None:
    """Get the built-in embedding space to bootstrap for a capability, if one is available."""
    space_key = _BOOTSTRAP_SPACE_KEYS.get(capability)
    if space_key is None:
        return None
    embedder = _get_or_load(space_key=space_key)
    if embedder is None or capability not in capabilities_of(embedder=embedder):
        return None
    return embedder.embedding_space_spec()


def reset() -> None:
    """Reset the registry and bootstrap defaults to built-ins. Intended for test isolation."""
    _registry.clear()
    _BOOTSTRAP_SPACE_KEYS.clear()
    _BOOTSTRAP_SPACE_KEYS.update(_DEFAULT_BOOTSTRAP_SPACE_KEYS)


def get_image_path_embedder(space_key: str) -> ImagePathEmbedder | None:
    """Get the space's image-path embedder, loading a built-in if needed."""
    _get_or_load(space_key=space_key)
    return _registry.get_image_path_embedder(space_key=space_key)


def get_image_crop_path_embedder(space_key: str) -> ImageCropPathEmbedder | None:
    """Get the space's image-crop-path embedder, loading a built-in if needed."""
    _get_or_load(space_key=space_key)
    return _registry.get_image_crop_path_embedder(space_key=space_key)


def get_video_path_embedder(space_key: str) -> VideoPathEmbedder | None:
    """Get the space's video-path embedder, loading a built-in if needed."""
    _get_or_load(space_key=space_key)
    return _registry.get_video_path_embedder(space_key=space_key)


def get_image_pil_embedder(space_key: str) -> ImagePILEmbedder | None:
    """Get the space's PIL-image embedder, loading a built-in if needed."""
    _get_or_load(space_key=space_key)
    return _registry.get_image_pil_embedder(space_key=space_key)


def get_text_embedder(space_key: str) -> TextEmbedder | None:
    """Get the space's text embedder, loading a built-in if needed."""
    _get_or_load(space_key=space_key)
    return _registry.get_text_embedder(space_key=space_key)


def _get_or_load(space_key: str) -> Embedder | None:
    return _registry.get(space_key) or _load_builtin(space_key=space_key)


def _load_builtin(space_key: str) -> Embedder | None:
    factory = _BUILTIN_SPACE_FACTORIES.get(space_key)
    if factory is None:
        return None
    embedder = factory()
    _registry.register(embedder=embedder)
    return embedder


def _create_mobileclip() -> Embedder:
    from lightly_studio.embed.mobileclip_embedder import MobileCLIPEmbedder  # noqa: PLC0415

    return MobileCLIPEmbedder()


def _create_perception_encoder() -> Embedder:
    from lightly_studio.embed.perception_encoder_embedder import (  # noqa: PLC0415
        PerceptionEncoderEmbedder,
    )

    return PerceptionEncoderEmbedder()


def _format_capabilities(capabilities: set[Capability]) -> str:
    return ", ".join(sorted(capability.value for capability in capabilities))


_BUILTIN_SPACE_FACTORIES: dict[str, Callable[[], Embedder]] = {
    "mobileclip_s0": _create_mobileclip,
    "PE-Core-T16-384": _create_perception_encoder,
}
