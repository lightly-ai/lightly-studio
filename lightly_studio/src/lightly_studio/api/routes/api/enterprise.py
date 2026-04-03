"""Enterprise-specific API routes."""

from __future__ import annotations

import os

from fastapi import APIRouter

enterprise_router = APIRouter()


@enterprise_router.put("/cloud-credentials")
def refresh_cloud_credentials(credentials: dict[str, str]) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables and clears the S3 fsspec
    instance cache so that subsequent file operations pick up the new
    credentials.
    """
    os.environ.update(credentials)

    # We currently support only AWS - this will need to be updated once we add support for other providers.
    from s3fs import S3FileSystem  # lazy: s3fs is an optional dependency

    S3FileSystem.clear_instance_cache()
