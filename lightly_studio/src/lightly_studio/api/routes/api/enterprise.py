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

    TODO Mihnea (04/2026) Security:
     This endpoint has no authentication and accepts arbitrary env var
     keys. This is acceptable for air-gapped on-prem (behind Docker isolation with no internet).
     For the hosted version, this endpoint must be secured with authentication and input validation.
    """
    apply_cloud_credentials(credentials=credentials)
