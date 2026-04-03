"""Enterprise-specific API routes."""

from __future__ import annotations

import os

from fastapi import APIRouter
from fsspec.spec import AbstractFileSystem

enterprise_router = APIRouter()


@enterprise_router.put("/cloud-credentials")
def refresh_cloud_credentials(credentials: dict[str, str]) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables and clears all fsspec
    filesystem instance caches so that subsequent file operations pick up the
    new credentials.
    """
    os.environ.update(credentials)
    AbstractFileSystem.clear_instance_cache()
