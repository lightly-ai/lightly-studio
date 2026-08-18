"""Anonymous ID identifying one LightlyStudio installation across runs."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR

logger = logging.getLogger(__name__)

# Shares the model cache directory so everything LightlyStudio writes sits under one path the user
# can delete. The directory is not model specific, despite the env var name.
INSTALL_ID_PATH: Path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / "install_id"


def get_install_id(path: Path = INSTALL_ID_PATH) -> UUID:
    """Get the anonymous ID for this installation, creating it on the first call.

    The ID is a random UUID carrying nothing about the machine or the user. Only call this when
    usage tracking is enabled, so that opting out leaves nothing behind on disk.

    Args:
        path: File holding the ID.

    Returns:
        The installation ID. A fresh one on every call if the file cannot be written.
    """
    install_id = _read_install_id(path=path)
    if install_id is not None:
        return install_id

    install_id = uuid4()
    _write_install_id(path=path, install_id=install_id)
    return install_id


def _read_install_id(path: Path) -> UUID | None:
    """Read the stored ID, or None if it is missing or unreadable."""
    try:
        return UUID(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _write_install_id(path: Path, install_id: UUID) -> None:
    """Store the ID, ignoring a read-only or full disk."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(install_id))
    except OSError:
        logger.debug(f"Could not store the installation ID at {path}.", exc_info=True)
