"""Derive and check annotation MCAP URIs.

An annotation MCAP sits next to its source recording and shares the stem plus a
suffix: `foo.mcap` → `foo_labeled.mcap`. It is not a recording of its own.
"""

from __future__ import annotations

import fsspec

from lightly_studio.core.mcap import add_mcaps

DEFAULT_ANNOTATION_MCAP_SUFFIX = "_labeled"


def annotation_mcap_uri(recording_uri: str, suffix: str = DEFAULT_ANNOTATION_MCAP_SUFFIX) -> str:
    """Return the URI of the annotation MCAP that belongs to a recording.

    Args:
        recording_uri: The path or URI of the source recording.
        suffix: Inserted before the `.mcap` extension.

    Returns:
        The annotation MCAP URI. `s3://` and local paths are rewritten the same way.
    """
    if recording_uri.endswith(add_mcaps.MCAP_EXTENSION):
        stem = recording_uri[: -len(add_mcaps.MCAP_EXTENSION)]
        return f"{stem}{suffix}{add_mcaps.MCAP_EXTENSION}"
    return f"{recording_uri}{suffix}{add_mcaps.MCAP_EXTENSION}"


def is_annotation_mcap(uri: str, suffix: str = DEFAULT_ANNOTATION_MCAP_SUFFIX) -> bool:
    """Return whether a URI names an annotation MCAP rather than a source recording.

    Args:
        uri: A path or URI that may point at an annotation MCAP.
        suffix: The annotation MCAP stem suffix, including the leading underscore.

    Returns:
        True if the file name ends with `{suffix}.mcap`.
    """
    return _file_name(uri).endswith(f"{suffix}{add_mcaps.MCAP_EXTENSION}")


def annotation_mcap_exists(uri: str) -> bool:
    """Return whether an annotation MCAP URI resolves on its filesystem.

    Uses fsspec, so `s3://` and `memory://` work the same as a local path.

    Args:
        uri: The path or URI to check.

    Returns:
        True if the file exists.
    """
    filesystem, path_in_filesystem = fsspec.core.url_to_fs(url=uri)
    return bool(filesystem.exists(path_in_filesystem))


def _file_name(uri: str) -> str:
    """Return the last path component of a local path or URI."""
    normalized = uri.replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", maxsplit=1)[-1]
