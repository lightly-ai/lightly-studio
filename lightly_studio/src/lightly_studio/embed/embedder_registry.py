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
_MOBILECLIP_SPACE_KEY = "mobileclip_s0"
_PERCEPTION_ENCODER_SPACE_KEY = "PE-Core-T16-384"
_INITIAL_BOOTSTRAP_SPACES = {
    Capability.IMAGE_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.IMAGE_CROP_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.VIDEO_PATH: _PERCEPTION_ENCODER_SPACE_KEY,
    Capability.IMAGE_PIL: _MOBILECLIP_SPACE_KEY,
}


class EmbedderRegistry:
    """Stores at most one embedder per embedding space.

    An embedder can provide several capabilities. The registry keeps one embedder
    per ``space_key``; registering another embedder for the same space replaces
    it. The typed getters return the space's embedder only when it implements the
    requested capability.
    """

    def __init__(self) -> None:
        """Create a registry with the built-in bootstrap choices."""
        self._space_key_to_embedder: dict[str, Embedder] = {}
        self._bootstrap_spaces = dict(_INITIAL_BOOTSTRAP_SPACES)

    def register(
        self,
        embedder: Embedder,
        bootstrap_for: set[Capability] | None = None,
    ) -> None:
        """Register an embedder for its embedding space.

        The embedding space is read from ``embedder.embedding_space_spec()``. If an
        embedder is already registered for the same space, it is replaced.

        Args:
            embedder: The embedder to register.
            bootstrap_for: Capabilities for which this embedder becomes the bootstrap
                choice. By default, all implemented capabilities are updated. An empty
                set leaves the bootstrap choices unchanged.

        Raises:
            ValueError: If the embedder implements no capability, or if it shares
                a ``space_key`` with an already registered embedder but does not
                match its spec.
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
            space_key=space_key,
            capabilities=capabilities,
            bootstrap_for=bootstrap_for,
        )

    def get_image_path_embedder(self, space_key: str | None = None) -> ImagePathEmbedder | None:
        """Get the space's embedder if it embeds images by path, else None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_PATH)
        return embedder if isinstance(embedder, ImagePathEmbedder) else None

    def get_image_crop_path_embedder(
        self, space_key: str | None = None
    ) -> ImageCropPathEmbedder | None:
        """Get the space's embedder if it embeds image crops by path, else None."""
        embedder = self._get_or_bootstrap(
            space_key=space_key, capability=Capability.IMAGE_CROP_PATH
        )
        return embedder if isinstance(embedder, ImageCropPathEmbedder) else None

    def get_video_path_embedder(self, space_key: str | None = None) -> VideoPathEmbedder | None:
        """Get the space's embedder if it embeds videos by path, else None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.VIDEO_PATH)
        return embedder if isinstance(embedder, VideoPathEmbedder) else None

    def get_image_pil_embedder(self, space_key: str | None = None) -> ImagePILEmbedder | None:
        """Get the space's embedder if it embeds PIL images, else None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_PIL)
        return embedder if isinstance(embedder, ImagePILEmbedder) else None

    def get_text_embedder(self, space_key: str | None = None) -> TextEmbedder | None:
        """Get the space's embedder if it embeds text, else None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.TEXT)
        return embedder if isinstance(embedder, TextEmbedder) else None

    def get_image_bytes_embedder(self, space_key: str | None = None) -> ImageBytesEmbedder | None:
        """Get the space's embedder if it embeds images by bytes, else None."""
        embedder = self._get_or_bootstrap(space_key=space_key, capability=Capability.IMAGE_BYTES)
        return embedder if isinstance(embedder, ImageBytesEmbedder) else None

    def _get_or_bootstrap(self, space_key: str | None, capability: Capability) -> Embedder | None:
        selected_key = (
            space_key if space_key is not None else self._bootstrap_spaces.get(capability)
        )
        if selected_key is None:
            return None
        embedder = self._space_key_to_embedder.get(selected_key)
        if embedder is None:
            embedder = _load_builtin_embedder(space_key=selected_key)
            if embedder is not None:
                self.register(embedder=embedder, bootstrap_for=set())
        capability_type = _CAPABILITY_TO_TYPE.get(capability)
        if capability_type is None or not isinstance(embedder, capability_type):
            return None
        return embedder

    def _set_bootstrap_defaults(
        self,
        space_key: str,
        capabilities: set[Capability],
        bootstrap_for: set[Capability] | None,
    ) -> None:
        """Set the space as the bootstrap default for requested capabilities it supports."""
        requested_capabilities = capabilities if bootstrap_for is None else bootstrap_for
        for capability in requested_capabilities.intersection(capabilities):
            self._bootstrap_spaces[capability] = space_key


_registry = EmbedderRegistry()


def get_registry() -> EmbedderRegistry:
    """Return the process-wide embedder registry."""
    return _registry


def _capabilities_of(embedder: Embedder) -> set[Capability]:
    """Get the capabilities an embedder implements, inferred from its type."""
    return {
        capability for capability, cls in _CAPABILITY_TO_TYPE.items() if isinstance(embedder, cls)
    }


def _load_builtin_embedder(space_key: str) -> Embedder | None:
    """Construct the built-in embedder for a known space key."""
    if space_key == _MOBILECLIP_SPACE_KEY:
        from lightly_studio.embed.mobileclip_embedder import MobileCLIPEmbedder  # noqa: PLC0415

        return MobileCLIPEmbedder()
    if space_key == _PERCEPTION_ENCODER_SPACE_KEY:
        from lightly_studio.embed.perception_encoder_embedder import (  # noqa: PLC0415
            PerceptionEncoderEmbedder,
        )

        return PerceptionEncoderEmbedder()
    return None
