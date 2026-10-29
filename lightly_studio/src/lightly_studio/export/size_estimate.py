"""Estimates how many bytes an export with images will download."""

from __future__ import annotations

from collections.abc import Sequence

import fsspec

from lightly_studio.dataset import remote_storage
from lightly_studio.utils import parallelize

_DEFAULT_SAMPLE_SIZE = 20


def estimate_total_bytes(
    file_paths: Sequence[str], sample_size: int = _DEFAULT_SAMPLE_SIZE
) -> int | None:
    """Estimates the total size of the files from the sizes of a few of them.

    Reads the size of up to `sample_size` files spread evenly over the list, so a few remote
    requests cover any number of images. Files that can't be read are left out of the average.

    Args:
        file_paths: Absolute file paths or URLs readable by fsspec.
        sample_size: How many files to read the size of.

    Returns:
        The average size of the sampled files times the number of files, or None when no
        sampled file could be read.
    """
    if not file_paths:
        return None
    step = max(1, len(file_paths) // sample_size)
    sampled = list(file_paths[::step][:sample_size])
    sizes = [
        size
        for size in parallelize.thread_imap_lazy(
            function=_file_size,
            iterable=sampled,
            max_workers=remote_storage.image_probe_workers(paths=sampled),
            buffer_size=len(sampled),
        )
        if size is not None
    ]
    if not sizes:
        return None
    return round(sum(sizes) / len(sizes) * len(file_paths))


def _file_size(path: str) -> int | None:
    try:
        filesystem, filesystem_path = fsspec.core.url_to_fs(path)
        return int(filesystem.size(filesystem_path))
    except (OSError, ValueError):
        return None
