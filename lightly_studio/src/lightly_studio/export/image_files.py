"""Copies image files into an export folder, from local or remote storage."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

import fsspec

from lightly_studio.dataset import remote_storage
from lightly_studio.utils import parallelize


def relative_image_paths(paths: Sequence[str]) -> list[str]:
    """Returns each path relative to the deepest folder that contains all paths.

    The relative paths keep the folder structure below that folder, so images with the
    same file name in different folders get different relative paths.

    Args:
        paths: Absolute image paths or URLs, for example ``s3://bucket/a/img.jpg``.

    Returns:
        The relative paths in the order of ``paths``, with ``/`` as separator.
    """
    split_paths = [path.replace("\\", "/").split("/") for path in paths]
    common_folder = _common_folder(split_paths=split_paths)
    return [_safe_relative_path(parts=parts[len(common_folder) :]) for parts in split_paths]


def copy_images(sources: Sequence[str], destinations: Sequence[Path]) -> None:
    """Copies images to local destinations, in parallel for remote sources.

    Args:
        sources: Absolute image paths or URLs readable by fsspec.
        destinations: Local destination file paths, one for each source. Missing parent
            folders are created.
    """
    remote_storage.configure_connections(paths=sources)
    max_workers = remote_storage.image_probe_workers(paths=sources)
    # Resolve filesystems on the caller thread so the workers share cached clients.
    copy_inputs = (
        _resolve_copy_input(source=source, destination=destination)
        for source, destination in zip(sources, destinations)
    )
    if max_workers == 1:
        for copy_input in copy_inputs:
            _copy_image(copy_input=copy_input)
        return
    for _ in parallelize.thread_imap_lazy(
        function=_copy_image,
        iterable=copy_inputs,
        max_workers=max_workers,
        buffer_size=max_workers,
    ):
        pass


def _common_folder(split_paths: Sequence[list[str]]) -> list[str]:
    """Returns the folder parts that all paths share, without the file names."""
    if not split_paths:
        return []
    common = split_paths[0][:-1]
    for parts in split_paths[1:]:
        folder = parts[:-1]
        length = 0
        while length < min(len(common), len(folder)) and common[length] == folder[length]:
            length += 1
        common = common[:length]
    return common


def _safe_relative_path(parts: Sequence[str]) -> str:
    """Joins path parts without a root, protocol, drive letter or parent reference.

    Paths with no common folder, such as local and remote paths mixed, keep their leading
    parts. Joined to the export folder as is, an absolute path would point back at the source.
    """
    kept = [part for part in parts if part not in ("", ".", "..") and not part.endswith(":")]
    return "/".join(kept)


def _resolve_copy_input(
    source: str, destination: Path
) -> tuple[fsspec.AbstractFileSystem, str, Path]:
    filesystem, filesystem_path = fsspec.core.url_to_fs(source)
    return filesystem, filesystem_path, destination


def _copy_image(copy_input: tuple[fsspec.AbstractFileSystem, str, Path]) -> None:
    """Copies one file from its filesystem to a local destination."""
    filesystem, filesystem_path, destination = copy_input
    destination.parent.mkdir(parents=True, exist_ok=True)
    with filesystem.open(filesystem_path, "rb") as source_file, destination.open("wb") as dest:
        shutil.copyfileobj(source_file, dest)
