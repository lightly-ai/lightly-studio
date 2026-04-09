"""Enterprise-specific API routes."""

from __future__ import annotations

import os

from fastapi import APIRouter

enterprise_router = APIRouter()


@enterprise_router.put("/cloud-credentials", status_code=204, response_model=None)
def refresh_cloud_credentials(credentials: dict[str, str]) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables and clears the S3 fsspec
    instance cache so that subsequent file operations pick up the new
    credentials.

    TODO Mihnea (04/2026) Security:
     This endpoint has no authentication and accepts arbitrary env var
     keys. This is acceptable for air-gapped on-prem (behind Docker isolation with no internet).
     For the hosted version, this endpoint must be secured with authentication and input validation.
    """
    os.environ.update(credentials)

    # We currently support only AWS - this will need to be updated once support for other providers.
    from s3fs import (  # type: ignore[import-untyped]  # noqa: PLC0415 lazy: s3fs is an optional dependency
        S3FileSystem,
    )

    S3FileSystem.clear_instance_cache()
