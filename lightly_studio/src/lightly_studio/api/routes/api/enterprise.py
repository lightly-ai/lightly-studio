"""Enterprise-specific API routes."""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import APIRouter, Header, HTTPException, status

enterprise_router = APIRouter()
logger = logging.getLogger(__name__)


@enterprise_router.put("/cloud-credentials", status_code=204, response_model=None)
def refresh_cloud_credentials(
    credentials: dict[str, str],
    authorization: str | None = Header(default=None),
) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables and clears the S3 fsspec
    instance cache so that subsequent file operations pick up the new
    credentials.
    """
    expected_token = os.getenv("LIGHTLY_STUDIO_ENTERPRISE_API_TOKEN")
    if expected_token is None:
        logger.warning("Rejected cloud credential update: enterprise API token is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud credential updates are disabled.",
        )

    if authorization is None or not authorization.startswith("Bearer "):
        logger.warning("Rejected cloud credential update: missing or invalid authorization header.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    provided_token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(provided_token, expected_token):
        logger.warning("Rejected cloud credential update: invalid token.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    os.environ.update(credentials)

    # We currently support only AWS - this will need to be updated once support for other providers.
    from s3fs import (  # type: ignore[import-untyped]  # noqa: PLC0415 lazy: s3fs is an optional dependency
        S3FileSystem,
    )

    S3FileSystem.clear_instance_cache()
    logger.info("Cloud credentials updated successfully.")
