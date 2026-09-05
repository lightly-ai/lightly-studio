"""Configuration for concurrent remote storage reads."""

from __future__ import annotations

from collections.abc import Iterable

import fsspec

from lightly_studio.dataset import env

_LOCAL_PROTOCOLS = frozenset(("file", "local"))


def is_remote(path: str) -> bool:
    """Return whether the path lives on remote storage rather than a local filesystem."""
    return fsspec.utils.get_protocol(path) not in _LOCAL_PROTOCOLS


def image_probe_workers(paths: Iterable[str]) -> int:
    """Return the configured worker count when any path is remote, otherwise one."""
    if any(is_remote(path) for path in paths):
        return env.LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS
    return 1


def configure_connections(paths: Iterable[str]) -> None:
    """Configure connection capacity for the supplied remote storage paths."""
    if not any(fsspec.utils.get_protocol(path) == "s3" for path in paths):
        return
    protocol_config = fsspec.config.conf.setdefault("s3", {})
    config_kwargs = dict(protocol_config.get("config_kwargs") or {})
    existing_pool_size = int(config_kwargs.get("max_pool_connections", 0))
    config_kwargs["max_pool_connections"] = max(
        existing_pool_size, env.LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS
    )
    protocol_config["config_kwargs"] = config_kwargs
