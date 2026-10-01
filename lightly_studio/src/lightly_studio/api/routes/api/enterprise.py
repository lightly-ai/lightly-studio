"""Enterprise-specific API routes."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.cloud_credentials import apply_cloud_credentials

enterprise_router = APIRouter()


@enterprise_router.put("/cloud-credentials", status_code=204, response_model=None)
def refresh_cloud_credentials(credentials: dict[str, str]) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables, updates fsspec's runtime
    configuration, and clears affected filesystem caches so subsequent file
    operations pick up the new credentials.

    Only ``AWS_*``, ``GOOGLE_APPLICATION_CREDENTIALS``, and ``FSSPEC_*`` keys
    are accepted; any other key is rejected with 400.

    Note: This endpoint has no bearer-token authentication. The deployment
    boundary (Docker network isolation, no public internet exposure) is the
    primary access control for on-prem installs.
    """
    apply_cloud_credentials(credentials=credentials)
