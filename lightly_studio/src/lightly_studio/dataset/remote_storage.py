"""Tuning for reads against remote (cloud) object storage.

Remote reads behave differently from local ones in two ways that the defaults get wrong for
an import workload:

- **Read-ahead is sized for streaming, not for header reads.** ``s3fs`` defaults to a 50 MiB
  read-ahead block, and the read-ahead cache clamps its range to the object size, so the first
  read of a small object fetches the whole thing. Reading only image dimensions therefore
  downloads the entire image. :func:`open_kwargs_for_path` caps the block size so a partial
  read stays partial.
- **Concurrency is capped by the HTTP connection pool.** botocore allows 10 pooled connections
  by default, which becomes the underlying connector limit, so extra reader threads queue
  instead of overlapping. :func:`read_workers_for_path` and
  :func:`apply_s3_connection_pool_config` size the worker count and the pool together.

Local paths keep the CPU-derived worker count and the backend's own open defaults:
``LocalFileSystem.open`` does not accept ``block_size``, and extra threads only add contention
on a local disk.
"""

from __future__ import annotations

import os
from typing import Any

import fsspec

from lightly_studio.dataset import env

PROTOCOL_SEPARATOR = "://"

# Object storage protocols, i.e. those whose reads cross a network and pay request latency.
CLOUD_PROTOCOLS = ("s3", "gs", "gcs", "azure", "abfs")

# Minimum HTTP connection pool size, matching botocore's own default. A pool smaller than the
# reader count would serialize readers, so the pool is never sized below this.
_MIN_POOL_CONNECTIONS = 10


def is_remote_path(path: str) -> bool:
    """Return whether ``path`` targets a cloud storage backend.

    Args:
        path: A path or URL, e.g. ``s3://bucket/key`` or ``/data/images``.

    Returns:
        ``True`` for a cloud protocol in :data:`CLOUD_PROTOCOLS`, ``False`` for a
        local path or any other protocol.
    """
    if PROTOCOL_SEPARATOR not in path:
        return False
    protocol = path.split(PROTOCOL_SEPARATOR, maxsplit=1)[0]
    return protocol in CLOUD_PROTOCOLS


def open_kwargs_for_path(path: str) -> dict[str, Any]:
    """Return ``fs.open`` keyword arguments tuned for reading part of ``path``.

    Caps the read-ahead block for remote paths so a header-only read does not fetch the whole
    object. Use this only where a partial read is expected; a full-object read is served fine
    by the backend default and gains nothing from a smaller block.

    The cache type is deliberately left at the backend default (read-ahead). Disabling caching
    would cut bytes further but split one header read into several round trips, which is slower
    over a high-latency link.

    Args:
        path: The path about to be opened.

    Returns:
        Keyword arguments to pass to ``fs.open``; empty for a local path, whose backend does
        not accept ``block_size``.
    """
    if not is_remote_path(path):
        return {}
    return {"block_size": env.LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE}


def read_workers_for_path(path: str) -> int:
    """Return the number of concurrent readers to use for ``path``.

    Args:
        path: A representative path for the read workload.

    Returns:
        The configured remote I/O concurrency for a cloud path, otherwise the CPU-derived
        worker count used elsewhere for local work.
    """
    if is_remote_path(path):
        return max(1, env.LIGHTLY_STUDIO_IO_CONCURRENCY)
    return cpu_workers()


def cpu_workers() -> int:
    """Return the thread count for CPU-bound work.

    Uses available cores - 1 (at least 1), capped at 16, matching the decode-thread and
    shared-executor conventions elsewhere in the codebase.
    """
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1 or 1, 16))


def apply_s3_connection_pool_config() -> None:
    """Raise the S3 HTTP connection pool so concurrent readers actually overlap.

    botocore pools 10 connections by default, which becomes the underlying connector limit and
    caps in-flight requests regardless of how many threads read. That shows up as no speedup from
    added concurrency, plus "connection pool is full" warnings.

    The setting is written into fsspec's runtime config rather than passed per call, so it reaches
    every reader without threading storage options through each ``url_to_fs`` site. Existing keys
    are merged, not replaced, so credentials already in the config survive.

    Idempotent, and safe to call again after a credential refresh -- which is required, because
    ``cloud_credentials.apply_cloud_credentials`` replaces the whole per-protocol config and would
    otherwise drop this setting.
    """
    protocol_config = fsspec.config.conf.setdefault("s3", {})
    config_kwargs = dict(protocol_config.get("config_kwargs") or {})
    # Never lower a pool size the deployment set explicitly.
    pool_size = max(config_kwargs.get("max_pool_connections", 0), _max_pool_connections())
    config_kwargs["max_pool_connections"] = pool_size
    protocol_config["config_kwargs"] = config_kwargs


def _max_pool_connections() -> int:
    """Resolve the S3 connection pool size, deriving it from the reader count if unset."""
    configured = env.LIGHTLY_STUDIO_S3_MAX_POOL_CONNECTIONS
    if configured > 0:
        return configured
    return max(_MIN_POOL_CONNECTIONS, env.LIGHTLY_STUDIO_IO_CONCURRENCY)
