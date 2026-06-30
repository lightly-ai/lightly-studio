"""File listing utilities using fsspec.

Handles local and remote paths, directories, and glob patterns.
"""

from __future__ import annotations

import itertools
import logging
import os
import string
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import fsspec
from tqdm import tqdm

# Constants
PROTOCOL_SEPARATOR = "://"
DEFAULT_PROTOCOL = "file"
PATH_SEPARATOR = "/"

# Glob pattern characters
GLOB_CHARS = ["*", "?", "[", "]"]

# Cloud storage protocols
CLOUD_PROTOCOLS = ("s3", "gs", "gcs", "azure", "abfs")

# Character set used to fan out cloud listings. A single flat cloud prefix can
# only be paginated serially, so to parallelize we issue one listing per possible
# leading substring of the object name. Alphanumeric covers hash/UUID/hex-style
# names (e.g. Open Images IDs). Override with LIGHTLY_STUDIO_LIST_PREFIXES.
DEFAULT_LIST_PREFIXES = string.digits + string.ascii_lowercase + string.ascii_uppercase

# How many leading characters each fan-out prefix spans. Depth 1 issues one
# listing per character (e.g. 62 listings); depth 2 issues one per character pair
# (e.g. 256 listings for a 16-char hex set), giving far higher concurrency for
# very large flat folders. Override with LIGHTLY_STUDIO_LIST_PREFIX_DEPTH. Names
# shorter than the depth (or with a non-charset character within it) require
# depth 1. Default 1 keeps behavior unchanged.
DEFAULT_LIST_PREFIX_DEPTH = 1

# Image file extensions
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def iter_files_from_path(
    path: str,
    allowed_extensions: set[str] | None = None,
    list_workers: int = 1,
) -> Iterator[str]:
    """List all files from a single path, handling directories, globs, and individual files.

    Args:
        path: A single path which can be:
            - Individual file path
            - Directory path (will list all files recursively)
            - Glob pattern
            - Remote path (s3://, gcs://, etc.)
        allowed_extensions: Optional set of allowed file extensions (e.g., {".jpg", ".png"}).
            If None, uses default IMAGE_EXTENSIONS.
        list_workers: Number of concurrent workers used to list a cloud directory. When
            greater than 1, the listing is fanned out across leading-character prefixes
            (see DEFAULT_LIST_PREFIXES) instead of paginated serially. Only applies to
            cloud protocols; local listing is unaffected.

    Yields:
        File paths as they are discovered, with progress tracking
    """
    seen: set[str] = set()
    extensions = allowed_extensions or IMAGE_EXTENSIONS
    with tqdm(desc="Discovering files", unit=" files", dynamic_ncols=True) as pbar:
        cleaned_path = str(path).strip()
        if not cleaned_path:
            return
        fs = _get_filesystem(cleaned_path)
        yield from _process_single_path_streaming(
            fs, cleaned_path, seen, pbar, extensions, list_workers
        )


def _process_single_path_streaming(
    fs: fsspec.AbstractFileSystem,
    path: str,
    seen: set[str],
    pbar: tqdm[Any],
    extensions: set[str],
    list_workers: int = 1,
) -> Iterator[str]:
    """Process a single path and yield matching image files.

    Handles different path types: individual files, directories, and glob patterns.

    Args:
        fs: The filesystem instance.
        path: The path to process (file, directory, or glob pattern).
        seen: Set of already processed paths to avoid duplicates.
        pbar: Progress bar instance for tracking progress.
        extensions: Set of allowed file extensions.
        list_workers: Number of concurrent workers for cloud directory listing.

    Yields:
        File paths that match the criteria.

    Raises:
        ValueError: If the path doesn't exist or is not an image file when expected.
    """
    if _is_glob_pattern(path):
        yield from _process_glob_pattern(fs, path, seen, pbar, extensions)
    elif not fs.exists(path):
        raise ValueError(f"Path does not exist: {path}")
    elif fs.isfile(path):
        if _is_image_file(path, extensions) and path not in seen:
            seen.add(path)
            pbar.update(1)
            yield path
        elif not _is_image_file(path, extensions):
            raise ValueError(f"File is not an image: {path}")
    elif fs.isdir(path):
        for file_path in _stream_files_from_directory(fs, path, extensions, list_workers):
            if file_path not in seen:
                seen.add(file_path)
                pbar.update(1)
                yield file_path


def _process_glob_pattern(
    fs: fsspec.AbstractFileSystem, path: str, seen: set[str], pbar: tqdm[Any], extensions: set[str]
) -> Iterator[str]:
    """Process glob pattern and yield matching image files.

    Args:
        fs: The filesystem instance.
        path: The glob pattern path.
        seen: Set of already processed paths to avoid duplicates.
        pbar: Progress bar instance for tracking progress.
        extensions: Set of allowed file extensions.

    Yields:
        File paths that match the glob pattern and allowed extensions.
    """
    matching_paths = fs.glob(path)
    for p in matching_paths:
        path_str = str(p)
        if _needs_protocol_prefix(path_str, fs):
            protocol = _get_protocol_string(fs)
            path_str = f"{protocol}{PROTOCOL_SEPARATOR}{path_str}"
        if fs.isfile(path_str) and _is_image_file(path_str, extensions) and path_str not in seen:
            seen.add(path_str)
            pbar.update(1)
            yield path_str


def _stream_files_from_directory(
    fs: fsspec.AbstractFileSystem, path: str, extensions: set[str], list_workers: int = 1
) -> Iterator[str]:
    """Stream files from a directory with progress tracking.

    Args:
        fs: The filesystem instance
        path: Directory path to list
        extensions: Set of allowed file extensions
        list_workers: Number of concurrent workers for cloud directory listing.

    Yields:
        File paths as they are discovered
    """
    try:
        protocol = _get_protocol_string(fs)
        if protocol in CLOUD_PROTOCOLS:
            if list_workers > 1:
                yield from _parallel_stream_cloud(fs, path, extensions, list_workers)
            else:
                yield from _stream_files_using_walk(fs, path, extensions)
        else:
            try:
                all_paths = fs.find(path, detail=False)
                for p in all_paths:
                    if fs.isfile(p) and _is_image_file(p, extensions):
                        yield p
            except Exception as e:
                logging.warning(f"fs.find() failed for {path}, trying alternative method: {e}")
                yield from _stream_files_using_walk(fs, path, extensions)
    except Exception as e:
        logging.error(f"Error streaming files from '{path}': {e}")


def _stream_files_using_walk(
    fs: fsspec.AbstractFileSystem, path: str, extensions: set[str]
) -> Iterator[str]:
    """Stream files using fs.walk() method.

    Args:
        fs: The filesystem instance.
        path: The directory path to walk.
        extensions: Set of allowed file extensions.

    Yields:
        File paths that match the allowed extensions.
    """

    def add_protocol_if_needed(p: str) -> str:
        if _needs_protocol_prefix(p, fs):
            protocol = _get_protocol_string(fs)
            return f"{protocol}{PROTOCOL_SEPARATOR}{p}"
        return p

    for root, _dirs, files in fs.walk(path):
        for file in files:
            if not root.endswith(PATH_SEPARATOR):
                full_path = f"{root}{PATH_SEPARATOR}{file}"
            else:
                full_path = f"{root}{file}"
            full_path = add_protocol_if_needed(full_path)
            if _is_image_file(full_path, extensions):
                yield full_path


def _parallel_stream_cloud(
    fs: fsspec.AbstractFileSystem,
    path: str,
    extensions: set[str],
    workers: int,
) -> Iterator[str]:
    """List a flat cloud directory concurrently by fanning out over name prefixes.

    A single cloud prefix can only be paginated serially (each page depends on the
    previous page's continuation token), so listing a large flat folder is slow. To
    parallelize, one ``glob`` is issued per leading-character prefix (e.g. ``.../a*``,
    ``.../b*``), each of which the backend serves as an independent prefix listing.
    Results are merged as they complete.

    The character set (DEFAULT_LIST_PREFIXES, override via LIGHTLY_STUDIO_LIST_PREFIXES)
    must cover every leading character of every object name; alphanumeric covers the
    common hash/UUID/hex naming (such as Open Images IDs). The fan-out spans
    LIGHTLY_STUDIO_LIST_PREFIX_DEPTH leading characters: depth 1 issues one listing per
    character, depth 2 one per character pair (e.g. 256 listings for hex), etc. Higher
    depth gives more concurrency for very large flat folders, but requires every object
    name to be at least ``depth`` characters long and to use only charset characters
    within that span.

    Args:
        fs: The filesystem instance.
        path: The cloud directory to list.
        extensions: Set of allowed file extensions.
        workers: Number of concurrent listing workers.

    Yields:
        Image file paths as each prefix listing completes.
    """
    base = path if path.endswith(PATH_SEPARATOR) else f"{path}{PATH_SEPARATOR}"
    charset = os.environ.get("LIGHTLY_STUDIO_LIST_PREFIXES", DEFAULT_LIST_PREFIXES)
    depth = max(
        1, int(os.environ.get("LIGHTLY_STUDIO_LIST_PREFIX_DEPTH", str(DEFAULT_LIST_PREFIX_DEPTH)))
    )
    prefixes = ("".join(combo) for combo in itertools.product(charset, repeat=depth))

    def _glob_prefix(prefix: str) -> list[str]:
        try:
            return [str(p) for p in fs.glob(f"{base}{prefix}*")]
        except Exception as e:  # noqa: BLE001 - one bad prefix shouldn't abort the listing
            logging.warning(f"Listing prefix '{base}{prefix}*' failed: {e}")
            return []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_glob_prefix, prefix): prefix for prefix in prefixes}
        for future in as_completed(futures):
            for path_str in future.result():
                if _needs_protocol_prefix(path_str, fs):
                    protocol = _get_protocol_string(fs)
                    path_str = f"{protocol}{PROTOCOL_SEPARATOR}{path_str}"
                if _is_image_file(path_str, extensions):
                    yield path_str


def _get_filesystem(path: str) -> fsspec.AbstractFileSystem:
    """Get the appropriate filesystem for the given path.

    Args:
        path: The path to determine the filesystem for. Can be local or remote.

    Returns:
        An fsspec filesystem instance appropriate for the path's protocol.

    Raises:
        ValueError: If the protocol cannot be determined or is invalid.
    """
    protocol = (
        path.split(PROTOCOL_SEPARATOR, maxsplit=1)[0]
        if PROTOCOL_SEPARATOR in path
        else DEFAULT_PROTOCOL
    )

    # Ensure protocol is a string, not a tuple
    if isinstance(protocol, (list, tuple)):
        protocol = protocol[0]

    return fsspec.filesystem(protocol)


def _is_glob_pattern(path: str) -> bool:
    """Check if a path contains glob pattern characters.

    Args:
        path: The path to check for glob patterns.

    Returns:
        True if the path contains glob pattern characters (*, ?, [, ]), False otherwise.
    """
    return any(char in path for char in GLOB_CHARS)


def _is_image_file(path: str, extensions: set[str]) -> bool:
    """Check if a file is an image based on its extension.

    Args:
        path: The file path to check.
        extensions: Set of allowed file extensions (e.g., {'.jpg', '.png'}).

    Returns:
        True if the file has an allowed image extension, False otherwise.
    """
    path_lower = path.lower()
    return any(path_lower.endswith(ext) for ext in extensions)


def _needs_protocol_prefix(path: str, fs: fsspec.AbstractFileSystem) -> bool:
    """Check if a path needs protocol prefix.

    Args:
        path: The path to check.
        fs: The filesystem instance.

    Returns:
        True if the path needs a protocol prefix (e.g., for cloud storage),
        False if it is a local path.
    """
    if PROTOCOL_SEPARATOR in path:
        return False

    if not hasattr(fs, "protocol"):
        return False

    protocol = getattr(fs, "protocol", DEFAULT_PROTOCOL)
    # Handle case where protocol is a tuple (common with fsspec)
    if isinstance(protocol, (list, tuple)):
        protocol = protocol[0]

    return str(protocol) != DEFAULT_PROTOCOL


def _get_protocol_string(fs: fsspec.AbstractFileSystem) -> str:
    """Get the protocol string from filesystem.

    Args:
        fs: The filesystem instance.

    Returns:
        The protocol string (e.g., 's3', 'file', 'gcs').
        Returns 'file' as default if protocol cannot be determined.
    """
    protocol = getattr(fs, "protocol", DEFAULT_PROTOCOL)
    if isinstance(protocol, (list, tuple)):
        return str(protocol[0])
    return str(protocol)
