"""Enterprise remote connection for LightlyStudio.

Provides ``connect`` to establish a database connection to a remote
LightlyStudio enterprise instance. The function exchanges an API key or JWT
token for the database engine URL, applies any server-provided cloud storage
credentials, and delegates to ``db_manager.connect``.
"""

from __future__ import annotations

import http
import logging

import requests
from pydantic import BaseModel, ValidationError

from lightly_studio.cloud_credentials import apply_cloud_credentials
from lightly_studio.database import db_manager
from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_API_KEY,
    LIGHTLY_STUDIO_API_URL,
    LIGHTLY_STUDIO_TOKEN,
)

logger = logging.getLogger(__name__)


class _EnterpriseConnectResponse(BaseModel):
    """Response model for the enterprise connect endpoint.

    Mirrors the server-side ``EnterpriseConnectResponse`` defined in the
    self-hosted auth service.
    """

    engine_url: str
    cloud_credentials: dict[str, str] | None = None


_ENTERPRISE_CONNECT_ENDPOINT = "/auth/api/v1/enterprise-connect"
_API_KEY_LOGIN_ENDPOINT = "/auth/api/v1/api-key-login"


def connect(
    api_url: str | None = None,
    token: str | None = None,
    api_key: str | None = None,
) -> None:
    """Connect to a remote LightlyStudio enterprise instance.

    Exchanges a JWT token or an API key for the connection configuration via
    the enterprise API, applies any server-provided cloud storage credentials
    to the local environment, then sets up the global database connection using
    ``db_manager.connect``.

    Parameters can be passed explicitly or read from environment variables
    ``LIGHTLY_STUDIO_API_URL``, ``LIGHTLY_STUDIO_TOKEN``, or
    ``LIGHTLY_STUDIO_API_KEY``. Each explicit parameter takes precedence over
    its corresponding environment variable.

    Args:
        api_url: Base URL of the LightlyStudio enterprise instance
            (e.g. ``"http://10.0.0.5:8100"``). Falls back to the
            ``LIGHTLY_STUDIO_API_URL`` environment variable.
        token: JWT token copied from the LightlyStudio enterprise GUI.
            Falls back to the ``LIGHTLY_STUDIO_TOKEN`` environment variable.
        api_key: API key generated in the LightlyStudio enterprise GUI.
            Falls back to the ``LIGHTLY_STUDIO_API_KEY`` environment variable.

    Raises:
        ValueError: If ``api_url`` is missing, or if both ``token`` and ``api_key``
            are missing/provided together.
        ConnectionError: If the enterprise instance is unreachable.
        PermissionError: If authentication or authorization fails.
        RuntimeError: If the server is not configured for remote connections.
    """
    api_url = api_url or LIGHTLY_STUDIO_API_URL
    if token is None:
        token = LIGHTLY_STUDIO_TOKEN
    if api_key is None:
        api_key = LIGHTLY_STUDIO_API_KEY

    if not api_url:
        raise ValueError(
            "api_url is required. Pass it explicitly or set the "
            "LIGHTLY_STUDIO_API_URL environment variable."
        )
    if bool(token) == bool(api_key):
        raise ValueError(
            "Exactly one of token or api_key must be provided. Pass one explicitly or via "
            "LIGHTLY_STUDIO_TOKEN / LIGHTLY_STUDIO_API_KEY environment variables."
        )

    # Strip trailing slash.
    api_url = api_url.rstrip("/")

    try:
        config = _fetch_connect_config(api_url=api_url, token=token, api_key=api_key)
    except (ConnectionError, PermissionError, RuntimeError):
        logger.exception("Failed to connect to LightlyStudio enterprise instance.")
        raise

    if config.cloud_credentials:
        apply_cloud_credentials(credentials=config.cloud_credentials)
        logger.info("Applied cloud credentials from LightlyStudio enterprise configuration.")
        for key in config.cloud_credentials:
            logger.info(f"  {key}: configured")

    db_manager.connect(db_url=config.engine_url)

    logger.info(f"Successfully connected to LightlyStudio enterprise instance at {api_url}.")


def _fetch_connect_config(
    api_url: str,
    token: str | None = None,
    api_key: str | None = None,
) -> _EnterpriseConnectResponse:
    """Call the enterprise endpoint to retrieve the connection configuration.

    Args:
        api_url: Base URL of the LightlyStudio enterprise instance.
        token: JWT bearer token.
        api_key: Enterprise API key.

    Returns:
        Parsed and validated response from the enterprise connect endpoint.

    Raises:
        ConnectionError: If the server is unreachable or SSL verification fails.
        PermissionError: If authentication or authorization fails.
        RuntimeError: If the server returns an unexpected error.
    """
    response = _execute_connect_request(api_url=api_url, token=token, api_key=api_key)

    if response.status_code == http.HTTPStatus.UNAUTHORIZED:
        msg = (
            "Authentication failed — token may have expired. Re-copy it from the LightlyStudio GUI."
            if token
            else "Authentication failed — invalid or expired API key."
        )
        raise PermissionError(msg)
    if response.status_code == http.HTTPStatus.FORBIDDEN:
        raise PermissionError("Access denied — admin role required.")
    if response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE:
        raise RuntimeError(
            "Server is not configured for remote connections. "
            "Check the enterprise deployment configuration."
        )
    if not response.ok:
        raise RuntimeError(
            f"Unexpected error from LightlyStudio ({response.status_code}): {response.text}"
        )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "Unexpected response from LightlyStudio: response body is not valid JSON."
        ) from None

    try:
        return _EnterpriseConnectResponse.model_validate(data)
    except ValidationError:
        raise RuntimeError(
            "Unexpected response from LightlyStudio: response body does not "
            "match expected schema (missing or invalid `engine_url`)."
        ) from None


def _execute_connect_request(
    api_url: str,
    token: str | None = None,
    api_key: str | None = None,
) -> requests.Response:
    """Execute the HTTP request for enterprise connection authentication."""
    try:
        return _send_connect_request(api_url=api_url, token=token, api_key=api_key)
    except (requests.exceptions.SSLError, requests.ConnectionError, requests.Timeout) as error:
        raise ConnectionError(_connection_error_message(api_url=api_url, error=error)) from error


def _send_connect_request(
    api_url: str,
    token: str | None,
    api_key: str | None,
) -> requests.Response:
    """Send the request for the selected authentication method."""
    if token is not None:
        return requests.get(
            url=f"{api_url}{_ENTERPRISE_CONNECT_ENDPOINT}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    if api_key is not None:
        return requests.post(
            url=f"{api_url}{_API_KEY_LOGIN_ENDPOINT}",
            json={"api_key": api_key},
            timeout=10,
        )
    raise ValueError("Either token or api_key is required to execute the connection request.")


def _connection_error_message(api_url: str, error: requests.RequestException) -> str:
    """Return a user-facing message for a request transport error."""
    if isinstance(error, requests.exceptions.SSLError):
        return (
            f"SSL error connecting to {api_url}. "
            "Verify the server's TLS certificate is trusted "
            "by your Python environment."
        )
    if isinstance(error, requests.ConnectionError):
        return (
            f"Could not reach LightlyStudio at {api_url}. "
            "Verify the URL and that the server is running."
        )
    return (
        f"Request to LightlyStudio at {api_url} timed out. "
        "Verify that the server is reachable and responsive."
    )
