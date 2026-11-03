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


def check_input_file(path: PathLike, description: str, suffix: str) -> None:
    """Check that an input file has the expected suffix and can be accessed.

    The check uses `fs.info()` and not `fs.isfile()`, because cloud filesystems such as
    s3fs make `isfile()` return False for credential and permission errors too.

    Args:
        path: Local path or fsspec URL of the file, for example `s3://bucket/labels.json`.
        description: Name of the file in error messages, for example
            "COCO annotations json file".
        suffix: The expected file suffix including the dot, for example ".json".

    Raises:
        ValueError: If the path does not end with `suffix`.
        FileNotFoundError: If no file exists at the path.
        IsADirectoryError: If the path is a directory.
        OSError: If the file cannot be accessed, for example because of missing credentials
            or permissions. The message names the underlying error.
    """
    path_str = str(path)
    if not path_str.endswith(suffix):
        raise ValueError(f"The {description} must end with '{suffix}', got: '{path_str}'")
    fs, fs_path = fsspec.core.url_to_fs(url=path_str)
    try:
        info = fs.info(fs_path)
    # `NotADirectoryError` is raised when a parent of the local path is a file.
    except (FileNotFoundError, NotADirectoryError) as error:
        raise FileNotFoundError(
            f"{description[0].upper()}{description[1:]} not found: '{path_str}'."
            f"{double_slash_hint(path=path_str)}"
        ) from error
    # Cloud filesystems raise their own error types, e.g. botocore's NoCredentialsError.
    except Exception as error:
        raise OSError(
            f"Could not access the {description} '{path_str}': {type(error).__name__}: {error}"
        ) from error
    if info.get("type") != "file":
        raise IsADirectoryError(f"The {description} is a directory, not a file: '{path_str}'")


def double_slash_hint(path: str) -> str:
    """Return a hint if the path has an empty segment, as in `bucket//file.json`."""
    _, path_without_protocol = fsspec.core.split_protocol(path)
    if "//" in path_without_protocol:
        return " The path contains '//'. Check for an extra slash."
    return ""
