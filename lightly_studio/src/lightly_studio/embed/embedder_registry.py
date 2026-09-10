"""Process-wide registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key`` and the bootstrap defaults that pick a
space for a capability when no collection default is saved yet. Callers look up an
embedder by the capability they need with the matching typed getter, which returns
the space's embedder only when it implements that capability, loading a built-in
embedder on demand. The registry never touches the database; persisting a
collection's default space is the caller's responsibility.
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

# Space keys of the built-in embedders that a registry can load lazily.
_MOBILECLIP_SPACE_KEY = "mobileclip_s0"
_PERCEPTION_ENCODER_SPACE_KEY = "PE-Core-T16-384"

# Bootstrap defaults every registry starts with: the space_key used to bootstrap a
# collection default for a capability when none is saved yet. Capabilities absent
# here (TEXT, IMAGE_BYTES) have no built-in default until an embedder registers for
# them. Any capability can still be bootstrapped once an embedder is registered.
_DEFAULT_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = {
    Capability.IMAGE_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.IMAGE_CROP_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.IMAGE_PIL: _MOBILECLIP_SPACE_KEY,
    Capability.VIDEO_PATH: _PERCEPTION_ENCODER_SPACE_KEY,
}


class EmbedderRegistry:
    """Stores at most one embedder per embedding space and the bootstrap defaults.

    An embedder can provide several capabilities. The registry keeps one embedder
    per ``space_key``; registering another embedder for the same space replaces it.
    Capabilities never compose across embedders, so a partial replacement replaces
    the whole space. Each capability maps to the ``space_key`` used to bootstrap a
    collection default when none is saved yet. The typed getters return the space's
    embedder only when it implements the requested capability, loading a built-in
    embedder on demand. Each instance owns its own state.
    """

    def __init__(self) -> None:
        """Create a registry seeded with the built-in bootstrap defaults."""
        self._space_key_to_embedder: dict[str, Embedder] = {}
        self._bootstrap_space_keys: dict[Capability, str] = dict(_DEFAULT_BOOTSTRAP_SPACE_KEYS)

    def register(self, embedder: Embedder, bootstrap_for: set[Capability] | None = None) -> None:
        """Register an embedder for its embedding space and update bootstrap defaults.

        The embedding space is read from ``embedder.embedding_space_spec()``. If an
        embedder is already registered for the same space, it is replaced. The
        embedder becomes the bootstrap default for the capabilities in
        ``bootstrap_for`` that it implements, replacing any previous default for
        those capabilities and leaving other defaults unchanged.

        Args:
            embedder: The embedder to register.
            bootstrap_for: The capabilities to make this the bootstrap default for.
                ``None`` means every capability the embedder implements. An empty
                set changes no defaults. Requested capabilities the embedder does
                not implement are ignored.

        Raises:
            ValueError: If the embedder implements no capability, or if it shares a
                ``space_key`` with an already registered embedder but does not match
                its spec. An incompatible replacement leaves the registry unchanged.
        """
        spec = embedder.embedding_space_spec()
        space_key = spec.space_key
        capabilities = _capabilities_of(embedder=embedder)
        if not capabilities:
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
        self._set_bootstrap_defaults(
            space_key=space_key, capabilities=capabilities, bootstrap_for=bootstrap_for
        )

    def get_bootstrap_space(self, capability: Capability) -> EmbeddingSpaceSpec | None:
        """Get the embedding space to bootstrap for a capability, or None if there is none.

        Loads the built-in default lazily when needed. Returns the spec of the
        selected provider, including a custom one, only when it supports the
        capability.
        """
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
        """Resolve the space's embedder, falling back to the capability's bootstrap default.

        An explicit ``space_key`` selects exactly that space with no fallback.
        ``None`` selects the capability's bootstrap key, or returns ``None`` when
        there is no such default. An already registered embedder wins, including a
        partial provider for a built-in key. Otherwise a known built-in is loaded and
        registered on demand; an unknown space returns ``None``.
        """
        if space_key is None:
            space_key = self._bootstrap_space_keys.get(capability)
        if space_key is None:
            return None
        registered = self._space_key_to_embedder.get(space_key)
        if registered is not None:
            return registered
        embedder = _load_builtin_embedder(space_key=space_key)
        if embedder is None:
            return None
        # Lazy loading only supplies an object for an already-chosen space; it must
        # not re-decide bootstrap defaults, e.g. loading PE for a video collection
        # must not replace the MobileCLIP image defaults.
        self.register(embedder=embedder, bootstrap_for=set())
        return embedder

    def _set_bootstrap_defaults(
        self,
        space_key: str,
        capabilities: set[Capability],
        bootstrap_for: set[Capability] | None,
    ) -> None:
        """Make the space the bootstrap default for its capabilities within ``bootstrap_for``.

        ``bootstrap_for`` of ``None`` means every capability the embedder implements.
        """
        defaults = capabilities if bootstrap_for is None else capabilities & bootstrap_for
        for capability in defaults:
            self._bootstrap_space_keys[capability] = space_key


# Process-wide registry shared by the app and by callers that look up embedders.
_registry = EmbedderRegistry()


def get_registry() -> EmbedderRegistry:
    """Get the process-wide embedder registry."""
    return _registry


def _capabilities_of(embedder: Embedder) -> set[Capability]:
    """Get the capabilities an embedder implements, inferred from its type."""
    return {
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    }


def _load_builtin_embedder(space_key: str) -> Embedder | None:
    """Construct the built-in embedder for a space key, or None if there is none.

    Imports lazily so that looking up one built-in does not import the other model.
    """
    if space_key == _MOBILECLIP_SPACE_KEY:
        from lightly_studio.embed.mobileclip_embedder import MobileCLIPEmbedder  # noqa: PLC0415

        return MobileCLIPEmbedder()
    if space_key == _PERCEPTION_ENCODER_SPACE_KEY:
        from lightly_studio.embed.perception_encoder_embedder import (  # noqa: PLC0415
            PerceptionEncoderEmbedder,
        )

        return PerceptionEncoderEmbedder()
    return None
