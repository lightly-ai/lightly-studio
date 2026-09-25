"""Registry that maps embedding spaces to embedders.

Holds at most one embedder per ``space_key``. Callers look up an embedder by the
capability they need with the matching typed getter, which returns the space's
embedder only when it implements that capability.

A getter that gets the stored configuration of a space also resolves an embedder that
nobody registered: it builds the one the configuration names.
"""

from __future__ import annotations

import logging
import threading
import time
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
from lightly_studio.embed.remote.errors import RemoteEmbedderCapabilityError, RemoteEmbedderError

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
# How long a configuration that could not be built is remembered as unusable.
_REMOTE_RETRY_DELAY_SECONDS = 30.0
_INITIAL_BOOTSTRAP_SPACES = {
    Capability.IMAGE_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.IMAGE_CROP_PATH: _MOBILECLIP_SPACE_KEY,
    Capability.VIDEO_PATH: _PERCEPTION_ENCODER_SPACE_KEY,
    Capability.IMAGE_PIL: _MOBILECLIP_SPACE_KEY,
    Capability.IMAGE_BYTES: _MOBILECLIP_SPACE_KEY,
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

    Calling a getter with the stored ``config`` of a space adds a third source, and the
    three rank per capability: a registration wins for the capabilities it implements,
    a configuration wins over a built-in.
    A registration is process-global and keyed on the space alone, while a configured
    embedder is cached per dataset, because the same space key in two datasets can name
    two backends.

    Caches are guarded by ``_lock``. An embedder is built outside it, under a lock per space.
    """

    def __init__(self) -> None:
        """Create a registry with the built-in bootstrap choices."""
        self._space_key_to_embedder: dict[str, Embedder] = {}
        self._space_key_to_builtin: dict[str, Embedder] = {}
        self._config_to_embedder: dict[tuple[UUID, str], tuple[EmbedderConfig, Embedder]] = {}
        # The flag is False for a server that answers but serves no usable capability
        self._config_to_failure: dict[tuple[UUID, str], tuple[EmbedderConfig, float, bool]] = {}
        self._bootstrap_spaces = dict(_INITIAL_BOOTSTRAP_SPACES)
        self._build_locks: dict[tuple[UUID | None, str], threading.Lock] = {}
        self._lock = threading.Lock()

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
                a ``space_key`` with an embedder the registry already holds, registered
                or built-in, but does not match its spec.
        """
        spec = embedder.embedding_space_spec()
        space_key = spec.space_key
        capabilities = _capabilities_of(embedder=embedder)
        if not capabilities:
            raise ValueError(f"Embedder {type(embedder).__name__!r} implements no capability.")
        with self._lock:
            registered = self._space_key_to_embedder.get(space_key)
            held = registered or self._space_key_to_builtin.get(space_key)
            if held is not None:
                held_spec = held.embedding_space_spec()
                if held_spec != spec:
                    raise ValueError(
                        f"Embedding space {space_key!r} is already in use as "
                        f"{held_spec}, cannot register the incompatible {spec}."
                    )
            if registered is not None:
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

    def is_remote_unavailable(self, config: EmbedderConfig) -> bool:
        """Get whether the embedding server of the configuration failed inside the retry window.

        The getters return None for an unusable server and for a space without the capability.
        This tells the two apart.
        """
        with self._lock:
            if not self._failed_recently(config=config):
                return False
            return self._config_to_failure[(config.dataset_id, config.space_key)][2]

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
                capability, and a ``config`` names its own space.
            capability: The capability the caller needs. It selects the bootstrap space.
            config: The stored configuration of the space, used only when no embedder
                registered for it implements the capability.

        Returns:
            The embedder of the space, or None if no source has one.
        """
        if config is not None:
            space_key = config.space_key
            if config.url is None:
                config = None
        with self._lock:
            if space_key is None:
                space_key = self._bootstrap_spaces.get(capability)
            if space_key is None:
                return None
            embedder = self._cached_embedder(
                space_key=space_key, capability=capability, config=config
            )
            if embedder is not None:
                return embedder
            if config is not None and self._failed_recently(config=config):
                return None
            build_lock = self._build_locks.setdefault(
                _build_key(space_key=space_key, config=config), threading.Lock()
            )
        with build_lock:
            with self._lock:
                embedder = self._cached_embedder(
                    space_key=space_key, capability=capability, config=config
                )
                if embedder is not None:
                    return embedder
                if config is not None and self._failed_recently(config=config):
                    return None
            if config is not None:
                self._build_from_config(config=config)
            else:
                self._build_builtin(space_key=space_key)
        with self._lock:
            return self._cached_embedder(space_key=space_key, capability=capability, config=config)

    def _cached_embedder(
        self, space_key: str, capability: Capability, config: EmbedderConfig | None
    ) -> Embedder | None:
        """Get the embedder the caches hold for the space, or None. Needs ``_lock``.

        A registration that lacks the capability gives way to a configuration. A
        configuration is served only by the embedder built from that same configuration,
        so a changed URL or a rotated key misses.
        """
        registered = self._space_key_to_embedder.get(space_key)
        if registered is not None and (
            config is None or isinstance(registered, _CAPABILITY_TO_TYPE[capability])
        ):
            return registered
        if config is None:
            return self._space_key_to_builtin.get(space_key)
        cached = self._config_to_embedder.get((config.dataset_id, config.space_key))
        if cached is None:
            return None
        cached_config, cached_embedder = cached
        return cached_embedder if cached_config == config else None

    def _failed_recently(self, config: EmbedderConfig) -> bool:
        """Get whether the configuration failed inside the retry window. Needs ``_lock``."""
        failure = self._config_to_failure.get((config.dataset_id, config.space_key))
        if failure is None:
            return False
        failed_config, failed_at, _ = failure
        if failed_config != config:
            return False
        return time.monotonic() - failed_at < _REMOTE_RETRY_DELAY_SECONDS

    def _build_from_config(self, config: EmbedderConfig) -> None:
        """Build the embedder of a configuration and cache it, or cache the failure."""
        # TODO(Iunir, 09/2026): Close the client of a replaced embedder when the remote
        # embedder gains a teardown hook.
        key = (config.dataset_id, config.space_key)
        try:
            embedder = embedder_config.build_remote(config=config)
        except RemoteEmbedderError as error:
            logger.warning(
                "Cannot use the embedding server at %s for space %r.",
                config.url,
                config.space_key,
                exc_info=True,
            )
            with self._lock:
                self._config_to_failure[key] = (
                    config,
                    time.monotonic(),
                    not isinstance(error, RemoteEmbedderCapabilityError),
                )
            return
        with self._lock:
            self._config_to_embedder[key] = (config, embedder)
            self._config_to_failure.pop(key, None)

    def _build_builtin(self, space_key: str) -> None:
        """Load the built-in embedder of a space and cache it apart from the registrations."""
        embedder = _load_builtin_embedder(space_key=space_key)
        if embedder is None:
            return
        with self._lock:
            self._space_key_to_builtin[space_key] = embedder

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


def _build_key(space_key: str, config: EmbedderConfig | None) -> tuple[UUID | None, str]:
    """Get the build lock key: per dataset for a configuration, per space for a built-in."""
    if config is not None:
        return (config.dataset_id, config.space_key)
    return (None, space_key)


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
