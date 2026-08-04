"""Utilities for applying cloud storage credentials."""

from __future__ import annotations

import os
import warnings
from typing import Any

import fsspec


def apply_cloud_credentials(credentials: dict[str, str]) -> None:
    """Apply cloud credentials to the process and invalidate cached filesystems.

    In addition to setting environment variables, this updates fsspec's runtime
    configuration. The latter is required when credentials arrive after fsspec
    has already been imported, as is the case for enterprise credential refreshes.

    Args:
        credentials: Environment variables supplied by the enterprise service.

    Raises:
        ValueError: If an FSSPEC_* value cannot be parsed by fsspec.
    """
    fsspec_config = _parse_fsspec_config(credentials=credentials)

    os.environ.update(credentials)
    for protocol, protocol_config in fsspec_config.items():
        # Replace instead of update so removed credential fields do not survive
        # a credential rotation.
        fsspec.config.conf[protocol] = protocol_config

    protocols = set(fsspec_config)
    if any(key.startswith("AWS_") for key in credentials):
        protocols.add("s3")
    if "GOOGLE_APPLICATION_CREDENTIALS" in credentials:
        protocols.add("gcs")

    for protocol in protocols:
        _clear_filesystem_cache(protocol=protocol)


def _parse_fsspec_config(credentials: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Parse only the fsspec environment variables supplied in this refresh."""
    config: dict[str, dict[str, Any]] = {}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            fsspec.config.set_conf_env(conf_dict=config, envdict=credentials)
    except UserWarning as error:
        raise ValueError("Invalid FSSPEC cloud credential configuration.") from error
    return config


def _clear_filesystem_cache(protocol: str) -> None:
    """Clear a protocol's instance cache when its implementation is installed."""
    try:
        filesystem_class = fsspec.get_filesystem_class(protocol=protocol)
    except ImportError:
        # No instance can have been cached when the optional implementation is
        # unavailable. fsspec will provide its normal installation hint on use.
        return
    filesystem_class.clear_instance_cache()
