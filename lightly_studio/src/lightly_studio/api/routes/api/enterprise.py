"""Enterprise-specific API routes."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header

from lightly_studio.cloud_credentials import apply_cloud_credentials
from lightly_studio.dataset import env
from lightly_studio.errors import ForbiddenError


def require_cloud_credentials_secret(
    x_cloud_credentials_secret: str = Header(default=""),
) -> None:
    """Rejects the request unless it sends the secret in LIGHTLY_STUDIO_CLOUD_CREDENTIALS_SECRET.

    Unset or empty, the environment variable rejects every request.

    Raises:
        ForbiddenError: If the secret is not set or the header does not match it.
    """
    expected = env.LIGHTLY_STUDIO_CLOUD_CREDENTIALS_SECRET
    if not expected or not hmac.compare_digest(
        x_cloud_credentials_secret.encode(), expected.encode()
    ):
        raise ForbiddenError("The cloud credentials secret is missing or wrong.")


enterprise_router = APIRouter(dependencies=[Depends(require_cloud_credentials_secret)])


@enterprise_router.put("/cloud-credentials", status_code=204, response_model=None)
def refresh_cloud_credentials(credentials: dict[str, str]) -> None:
    """Receive cloud storage credentials.

    Sets the credentials as environment variables, updates fsspec's runtime
    configuration, and clears affected filesystem caches so subsequent file
    operations pick up the new credentials.

    Only ``AWS_*``, ``GOOGLE_APPLICATION_CREDENTIALS``, and ``FSSPEC_*`` keys
    are accepted; any other key is rejected with 400.

    The caller must send the secret set in ``LIGHTLY_STUDIO_CLOUD_CREDENTIALS_SECRET``
    in the ``X-Cloud-Credentials-Secret`` header. Otherwise the request gets 403.
    """
    apply_cloud_credentials(credentials=credentials)
