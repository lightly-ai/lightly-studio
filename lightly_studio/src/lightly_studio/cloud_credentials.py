"""Utilities for applying cloud storage credentials."""

from __future__ import annotations

import json
import os
import re
import threading
import warnings
from typing import Any, cast

import fsspec

from lightly_studio import ca_bundle

# Keys accepted by apply_cloud_credentials. Only well-known cloud provider
# environment variables are allowed to prevent arbitrary process-environment
# injection through the enterprise credential endpoint.
_ALLOWED_KEY_PATTERN = re.compile(
    r"^("
    r"AWS_[A-Z0-9_]+"
    r"|GOOGLE_APPLICATION_CREDENTIALS"
    r"|FSSPEC_[A-Z0-9_]+"
    r")$"
)

# PEM text of custom CA certificates for S3. botocore needs a file path in AWS_CA_BUNDLE, so
# this value is written to a file instead of being set as an environment variable.
_AWS_CA_BUNDLE_PEM_KEY = "AWS_CA_BUNDLE_PEM"
_AWS_CA_BUNDLE_KEY = "AWS_CA_BUNDLE"

# Serializes changes to the process environment, the fsspec configuration, and the CA bundle
# files. The studio server applies credentials in worker threads.
_apply_lock = threading.Lock()


def apply_cloud_credentials(credentials: dict[str, str]) -> None:
    """Apply cloud credentials to the process and invalidate cached filesystems.

    In addition to setting environment variables, this updates fsspec's runtime
    configuration. The latter is required when credentials arrive after fsspec
    has already been imported, as is the case for enterprise credential refreshes.

    Args:
        credentials: Environment variables supplied by the enterprise service.
            Keys must match one of the allowed cloud provider patterns
            (``AWS_*``, ``GOOGLE_APPLICATION_CREDENTIALS``, ``FSSPEC_*``).
            ``AWS_CA_BUNDLE_PEM`` holds custom CA certificates for S3. They are
            written to a file that ``AWS_CA_BUNDLE`` points to.

    Raises:
        ValueError: If a key is not in the allowlist, if an FSSPEC_* value
            cannot be parsed by fsspec, or if the CA certificates are not valid.
        ImportError: If a required cloud filesystem dependency is not installed.
    """
    _validate_credential_keys(credentials=credentials)
    fsspec_config = _parse_fsspec_config(credentials=credentials)

    has_aws = any(key.startswith("AWS_") for key in credentials)
    protocols = set(fsspec_config)
    if has_aws:
        protocols.add("s3")
    if "GOOGLE_APPLICATION_CREDENTIALS" in credentials:
        protocols.add("gcs")

    filesystem_classes = [
        _get_filesystem_class(protocol=protocol) for protocol in sorted(protocols)
    ]

    with _apply_lock:
        ca_bundle_path = _write_ca_bundle(credentials=credentials)

        _remove_stale_provider_env_vars(credentials=credentials)
        os.environ.update(
            {key: value for key, value in credentials.items() if key != _AWS_CA_BUNDLE_PEM_KEY}
        )
        if has_aws:
            if ca_bundle_path is not None:
                os.environ[_AWS_CA_BUNDLE_KEY] = ca_bundle_path
            ca_bundle.delete_ca_bundles(keep=ca_bundle_path)
        for protocol, protocol_config in fsspec_config.items():
            # Replace instead of update so removed credential fields do not survive
            # a credential rotation.
            fsspec.config.conf[protocol] = protocol_config

        for filesystem_class in filesystem_classes:
            filesystem_class.clear_instance_cache()


def _validate_credential_keys(credentials: dict[str, str]) -> None:
    """Raise ValueError for any key not in the cloud provider allowlist."""
    rejected = [key for key in credentials if not _ALLOWED_KEY_PATTERN.match(key)]
    if rejected:
        raise ValueError(
            f"Credential keys are not allowed: {rejected}. "
            "Only AWS_*, GOOGLE_APPLICATION_CREDENTIALS, and FSSPEC_* keys are accepted."
        )


def _write_ca_bundle(credentials: dict[str, str]) -> str | None:
    """Write the custom CA certificates to a file and return its path, if present."""
    pem = credentials.get(_AWS_CA_BUNDLE_PEM_KEY)
    if pem is None:
        return None
    if _AWS_CA_BUNDLE_KEY in credentials:
        raise ValueError(
            f"Credential keys {_AWS_CA_BUNDLE_KEY} and {_AWS_CA_BUNDLE_PEM_KEY} "
            "cannot be used together."
        )
    return ca_bundle.write_ca_bundle(pem=pem)


def _remove_stale_provider_env_vars(credentials: dict[str, str]) -> None:
    """Remove previously managed env vars for each provider present in the new payload.

    Ensures that keys omitted from a rotation (e.g. AWS_SESSION_TOKEN dropped
    when switching from temporary to long-term credentials, or a removed
    FSSPEC_* key) do not linger in the process environment and mislead later
    cloud clients.

    Only provider families that appear in the incoming payload are touched, so a
    GCS-only refresh never clears AWS variables.
    """
    has_aws = any(key.startswith("AWS_") for key in credentials)
    has_gcs = "GOOGLE_APPLICATION_CREDENTIALS" in credentials
    has_fsspec = any(key.startswith("FSSPEC_") for key in credentials)

    stale_keys = [
        key
        for key in os.environ
        if (has_aws and key.startswith("AWS_") and _ALLOWED_KEY_PATTERN.match(key))
        or (has_gcs and key == "GOOGLE_APPLICATION_CREDENTIALS")
        or (has_fsspec and key.startswith("FSSPEC_") and _ALLOWED_KEY_PATTERN.match(key))
    ]
    for key in stale_keys:
        del os.environ[key]


def _parse_fsspec_config(credentials: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Parse only the fsspec environment variables supplied in this refresh.

    Args:
        credentials: Mapping of environment variable names to their values,
            as returned by the credentials refresh endpoint.

    Returns:
        Nested fsspec config dict mapping protocol name to its settings.

    Raises:
        ValueError: If any credential key is not a valid fsspec environment variable.
    """
    config: dict[str, dict[str, Any]] = {}
    try:
        for key, value in credentials.items():
            # FSSPEC_<PROTOCOL> keys (exactly one underscore) carry a full JSON config blob
            # for that protocol. fsspec.config.set_conf_env handles per-key vars like
            # FSSPEC_S3_KEY itself, but the blob form must be pre-parsed into conf_dict.
            if key.startswith("FSSPEC_") and key.count("_") == 1:
                protocol_config = json.loads(value)
                if not isinstance(protocol_config, dict):
                    raise ValueError("FSSPEC protocol configuration must be a JSON object.")
                protocol = key.removeprefix("FSSPEC_").lower()
                config[protocol] = protocol_config
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            fsspec.config.set_conf_env(conf_dict=config, envdict=credentials)
    except (ValueError, UserWarning) as error:
        raise ValueError("Invalid FSSPEC cloud credential configuration.") from error
    return config


def _get_filesystem_class(protocol: str) -> type[Any]:
    """Return a filesystem class or raise an actionable dependency error."""
    try:
        return cast(type[Any], fsspec.get_filesystem_class(protocol=protocol))
    except ImportError as error:
        raise ImportError(
            f"Cloud storage credentials require support for the '{protocol}' protocol. "
            'Install it with pip install "lightly-studio[cloud-storage]".'
        ) from error
