"""File manipulation utilities."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

import requests
import xxhash

logger = logging.getLogger(__name__)


def download_file_if_does_not_exist(url: str, local_filename: Path) -> None:
    """Download a file from a URL if it does not already exist locally.

    Downloads to a temp file first, then moves to the final location only on success.
    This prevents corrupted partial downloads.

    Args:
        url: URL to download from.
        local_filename: Path where the file should be saved.
    """
    if local_filename.exists():
        return

    dir_name = local_filename.parent
    dir_name.mkdir(parents=True, exist_ok=True)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False, mode="wb") as tmp_file:
            tmp_path = tmp_file.name
            logger.info(f"Downloading {url} to {local_filename}")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, tmp_file)
        os.replace(tmp_path, local_filename)
    finally:
        # Clean up temp file if it still exists (download failed or move failed)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")


def get_file_xxhash(file_path: Path) -> str:
    """Calculate the xxhash of a file.

    XXHash is a fast non-cryptographic hash function.

    Args:
        file_path: Path to the file.

    Returns:
        The xxhash of the file as a string.
    """
    hasher = xxhash.xxh64()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
