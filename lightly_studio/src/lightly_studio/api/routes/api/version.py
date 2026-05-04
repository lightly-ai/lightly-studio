"""This module contains the API route for version information."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter

from lightly_studio.export_version import get_version_info

version_router = APIRouter(tags=["version"])
package_root = Path(__file__).resolve().parent.parent.parent.parent
version_file = package_root / "dist_lightly_studio_view_app_app" / "version.json"


@dataclass
class RuntimeVersionInfo:
    """Runtime version information returned by the version endpoint."""

    version: str
    git_sha: str
    is_tagged_commit: bool


def _load_version_info_from_file() -> RuntimeVersionInfo | None:
    """Load runtime version info from build-generated version.json."""
    try:
        with version_file.open() as f:
            data = json.load(f)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    version = data.get("version")
    git_sha = data.get("git_sha")
    is_tagged_commit = data.get("is_tagged_commit")
    if (
        not isinstance(version, str)
        or not isinstance(git_sha, str)
        or not isinstance(is_tagged_commit, bool)
    ):
        return None
    return RuntimeVersionInfo(
        version=version,
        git_sha=git_sha,
        is_tagged_commit=is_tagged_commit,
    )


@version_router.get("/version")
def get_version() -> RuntimeVersionInfo:
    """Get backend runtime version information.

    Prefer the build-generated version file and fall back to runtime generation.
    """
    file_version_info = _load_version_info_from_file()
    if file_version_info is not None:
        return file_version_info

    runtime_version_info = get_version_info()
    return RuntimeVersionInfo(
        version=runtime_version_info["version"],
        git_sha=runtime_version_info["git_sha"],
        is_tagged_commit=runtime_version_info["is_tagged_commit"],
    )
