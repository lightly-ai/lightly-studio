"""Enterprise-specific API routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader

enterprise_router = APIRouter()

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

_ALLOWED_CREDENTIAL_KEYS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_DEFAULT_REGION",
        "AWS_ENDPOINT_URL",
        "AWS_S3_ALLOW_UNSAFE_RENAME",
    }
)


@enterprise_router.put("/cloud-credentials", status_code=204, response_model=None)
def refresh_cloud_credentials(
    credentials: dict[str, str],
    api_key: str | None = Security(_API_KEY_HEADER),
) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables and clears the S3 fsspec
    instance cache so that subsequent file operations pick up the new
    credentials.
    """
    expected_api_key = os.environ.get("LIGHTLY_STUDIO_API_KEY")
    if not expected_api_key or api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    invalid_keys = set(credentials) - _ALLOWED_CREDENTIAL_KEYS
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid credential keys: {sorted(invalid_keys)}",
        )

    os.environ.update(credentials)

    # We currently support only AWS - this will need to be updated once support for other providers.
    from s3fs import (  # type: ignore[import-untyped]  # noqa: PLC0415 lazy: s3fs is an optional dependency
        S3FileSystem,
    )

    S3FileSystem.clear_instance_cache()
