"""Shared file path helpers for media ingestion."""

from __future__ import annotations

from pathlib import Path

import fsspec

from lightly_studio.type_definitions import PathLike


def normalize_path_root(path: PathLike) -> str:
    """Return an absolute local path and preserve a remote path as-is.

    Local paths are returned in posix form (forward slashes) so they can be
    safely joined with `posixpath.join` and compared across platforms. On
    Windows, `str(Path(...).absolute())` yields backslashes that, when joined
    with posix-separated relative paths, produce mixed-separator strings that
    fail to match what was stored at ingestion time.

    Shared by image and video ingestion so both modalities store and compare
    `file_path_abs` values consistently.
    """
    path_str = str(path)
    protocol, _ = fsspec.core.split_protocol(path_str)
    if protocol is None:
        return Path(path_str).absolute().as_posix()
    if protocol == "file":
        return Path(fsspec.core.strip_protocol(path_str)).absolute().as_posix()
    return path_str
