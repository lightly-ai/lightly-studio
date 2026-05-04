"""This module contains the API route for version information."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from lightly_studio.export_version import get_version_info

version_router = APIRouter(tags=["version"])
package_root = Path(__file__).resolve().parent.parent.parent.parent
version_file = package_root / "dist_lightly_studio_view_app_app" / "version.json"


def _load_version_info_from_file() -> tuple[str, str] | None:
    """Load version and git SHA from build-generated version.json."""
    try:
        with version_file.open() as f:
            data = json.load(f)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    version = data.get("version")
    git_sha = data.get("git_sha")
    if not isinstance(version, str) or not isinstance(git_sha, str):
        return None
    return version, git_sha


@version_router.get("/version")
def get_version() -> dict[str, str]:
    """Get backend version and git SHA at runtime.

    Prefer the build-generated version file and fall back to runtime generation.
    """
    file_version_info = _load_version_info_from_file()
    if file_version_info is not None:
        version, git_sha = file_version_info
        return {"version": version, "git_sha": git_sha}

    runtime_version_info = get_version_info()
    return {
        "version": runtime_version_info["version"],
        "git_sha": runtime_version_info["git_sha"],
    }
