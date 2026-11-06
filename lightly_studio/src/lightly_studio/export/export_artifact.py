"""Remove the files of export jobs."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_export_artifact(export_path: str) -> None:
    """Best-effort removal of an export job's on-disk artifact.

    Every ``export_path`` is generated under the system temp directory (see
    ``lightly_studio.api.routes.api.export``); paths outside of it are left untouched rather than
    removed, since they cannot be confirmed to be export-owned.

    Args:
        export_path: Absolute path to the export job's file or directory.
    """
    resolved_path = Path(export_path).resolve()
    temp_dir = Path(tempfile.gettempdir()).resolve()
    try:
        relative_path = resolved_path.relative_to(temp_dir)
    except ValueError:
        logger.warning("Skipping export artifact outside the temp directory: %s", export_path)
        return
    if relative_path == Path():
        # Equality is not raised by `relative_to`; reject the temp directory root itself.
        logger.warning(
            "Skipping export artifact that is the temp directory itself: %s", export_path
        )
        return
    if resolved_path.is_dir():
        shutil.rmtree(resolved_path, ignore_errors=True)
        return
    try:
        resolved_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove export artifact: %s", export_path, exc_info=True)
