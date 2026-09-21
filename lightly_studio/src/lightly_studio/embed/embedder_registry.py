"""Registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key``. Callers look up an embedder by the
capability they need with the matching typed getter, which returns the space's
embedder only when it implements that capability.

A getter that gets the stored configuration of a space also resolves an embedder that
nobody registered: it builds the one the configuration names and caches it per dataset.
"""

from __future__ import annotations

import logging
from collections.abc import Set
from uuid import UUID

from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)

from lightly_studio.embed import embedder_config
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.remote.errors import RemoteEmbedderError

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

    Calling a getter without a ``space_key`` selects that capability's bootstrap
    space. Initially, MobileCLIP and Perception Encoder serve as default bootstraps
    for preselected capabilities. Bootstraps are updated when a custom embedder is registered.

    Calling a getter with the stored ``config`` of a space adds a third source: a space
    that no embedder is registered for resolves to the embedder its configuration names.
    Registered embedders are process-global and keyed on the space alone, while embedders
    built from a configuration are cached per dataset, because the same space key in two
    datasets can name two backends. A registered embedder wins over a configuration, so a
    call to ``register`` is never overridden by a stored row.
    """

    def __init__(self) -> None:
        """Create a registry with the built-in bootstrap choices."""
        self._space_key_to_embedder: dict[str, Embedder] = {}
        self._config_to_embedder: dict[tuple[UUID, str], tuple[EmbedderConfig, Embedder]] = {}
        self._bootstrap_spaces = dict(_INITIAL_BOOTSTRAP_SPACES)

    def register(
        self,
        embedder: Embedder,
        bootstrap_for: Set[Capability] | None = None,
    ) -> None:
        """Register an embedder for its embedding space.

        The embedding space is read from ``embedder.embedding_space_spec()``. If an
        embedder is already registered for the same space, it is replaced.

        Args:
            embedder: The embedder to register.
            bootstrap_for: Capabilities for which this embedder becomes the bootstrap
                choice. By default, all implemented capabilities are updated. An empty
                set leaves the bootstrap choices unchanged. Requested capabilities
                the embedder does not implement are ignored.

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

    def get_image_path_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> ImagePathEmbedder | None:
        """Get the space's embedder if it embeds images by path, else None."""
        embedder = self._resolve(
            space_key=space_key, capability=Capability.IMAGE_PATH, config=config
        )
        return embedder if isinstance(embedder, ImagePathEmbedder) else None

    def get_image_crop_path_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> ImageCropPathEmbedder | None:
        """Get the space's embedder if it embeds image crops by path, else None."""
        embedder = self._resolve(
            space_key=space_key, capability=Capability.IMAGE_CROP_PATH, config=config
        )
        return embedder if isinstance(embedder, ImageCropPathEmbedder) else None

    def get_video_path_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> VideoPathEmbedder | None:
        """Get the space's embedder if it embeds videos by path, else None."""
        embedder = self._resolve(
            space_key=space_key, capability=Capability.VIDEO_PATH, config=config
        )
        return embedder if isinstance(embedder, VideoPathEmbedder) else None

    def get_image_pil_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> ImagePILEmbedder | None:
        """Get the space's embedder if it embeds PIL images, else None."""
        embedder = self._resolve(
            space_key=space_key, capability=Capability.IMAGE_PIL, config=config
        )
        return embedder if isinstance(embedder, ImagePILEmbedder) else None

    def get_text_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> TextEmbedder | None:
        """Get the space's embedder if it embeds text, else None."""
        embedder = self._resolve(space_key=space_key, capability=Capability.TEXT, config=config)
        return embedder if isinstance(embedder, TextEmbedder) else None

    def get_image_bytes_embedder(
        self, space_key: str | None = None, config: EmbedderConfig | None = None
    ) -> ImageBytesEmbedder | None:
        """Get the space's embedder if it embeds images by bytes, else None."""
        embedder = self._resolve(
            space_key=space_key, capability=Capability.IMAGE_BYTES, config=config
        )
        return embedder if isinstance(embedder, ImageBytesEmbedder) else None

    def preload_builtin_embedders(self) -> None:
        """Load and cache the built-in bootstrap embedders.

        Enterprise deployments call this to cache the weights ahead of first use.
        """
        for capability in self._bootstrap_spaces:
            self._resolve(space_key=None, capability=capability, config=None)

    def _resolve(
        self, space_key: str | None, capability: Capability, config: EmbedderConfig | None
    ) -> Embedder | None:
        """Resolve the embedder of a space from a registration, a configuration or a built-in.

        Args:
            space_key: The space to resolve. None selects the bootstrap space of the
                capability. A configuration names its own space, so ``space_key`` is
                ignored when one is given.
            capability: The capability the caller needs. It selects the bootstrap space.
            config: The stored configuration of the space. It is used only when no
                embedder is registered for the space.

        Returns:
            The embedder of the space, or None if no source has one.
        """
        if config is not None:
            space_key = config.space_key
        if space_key is None:
            space_key = self._bootstrap_spaces.get(capability)
        if space_key is None:
            return None
        registered = self._space_key_to_embedder.get(space_key)
        if registered is not None:
            return registered
        if config is not None and config.url is not None:
            return self._embedder_from_config(config=config)
        return self._builtin_embedder(space_key=space_key)

    def _embedder_from_config(self, config: EmbedderConfig) -> Embedder | None:
        """Build and cache the embedder that a stored configuration names.

        The cache holds the configuration the embedder was built from, so a changed URL or
        a rotated key builds a new embedder instead of serving the old one. It is keyed on
        the dataset as well, so two datasets that share a space key keep their own backend.
        The embedder is cached before any capability is asked of it, so a dataset reads
        ``/v1/describe`` once and not once per capability.

        Returns:
            The embedder of the configuration, or None if the server serves none. Such a
            server reads like a space with no embedder, which every caller already handles.
        """
        # TODO(Iunir, 09/2026): Close the client of a replaced embedder when the remote
        # embedder gains a teardown hook.
        key = (config.dataset_id, config.space_key)
        cached = self._config_to_embedder.get(key)
        if cached is not None:
            cached_config, cached_embedder = cached
            if cached_config == config:
                return cached_embedder
        try:
            embedder = embedder_config.build_remote(config=config)
        except RemoteEmbedderError:
            logger.warning(
                "Cannot use the embedding server at %s for space %r.",
                config.url,
                config.space_key,
                exc_info=True,
            )
            return None
        self._config_to_embedder[key] = (config, embedder)
        return embedder

    def _builtin_embedder(self, space_key: str) -> Embedder | None:
        """Lazily load and register the built-in embedder of a space."""
        embedder = _load_builtin_embedder(space_key=space_key)
        if embedder is None:
            return None
        self.register(embedder=embedder, bootstrap_for=set())
        return embedder

    def _set_bootstrap_defaults(
        self,
        space_key: str,
        capabilities: set[Capability],
        bootstrap_for: Set[Capability] | None,
    ) -> None:
        """Set the space as the bootstrap default for requested capabilities it supports."""
        defaults = (
            capabilities if bootstrap_for is None else capabilities.intersection(bootstrap_for)
        )
        for capability in defaults:
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
