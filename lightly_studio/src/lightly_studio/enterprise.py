"""Enterprise remote connection for LightlyStudio.

Provides ``connect`` to establish a database connection to a remote
LightlyStudio enterprise instance. The function exchanges a JWT token
for the database engine URL and delegates to ``db_manager.connect``.
"""

from __future__ import annotations

import http

import requests

from lightly_studio import db_manager
from lightly_studio.dataset.env import LIGHTLY_STUDIO_API_URL, LIGHTLY_STUDIO_TOKEN

_DB_CONNECT_ENDPOINT = "/auth/api/v1/db-connect-engine-url"


def connect(
    api_url: str | None = None,
    token: str | None = None,
) -> None:
    """Connect to a remote LightlyStudio enterprise instance.

    Exchanges the JWT token for a database engine URL via the enterprise API,
    then sets up the global database connection using ``db_manager.connect``.

    Parameters can be passed explicitly or read from environment variables
    ``LIGHTLY_STUDIO_API_URL`` and ``LIGHTLY_STUDIO_TOKEN``. Explicit
    parameters take precedence.

    Args:
        api_url: Base URL of the LightlyStudio enterprise instance
            (e.g. ``"http://10.0.0.5:8100"``). Falls back to the
            ``LIGHTLY_STUDIO_API_URL`` environment variable.
        token: JWT token copied from the LightlyStudio enterprise GUI.
            Falls back to the ``LIGHTLY_STUDIO_TOKEN`` environment variable.

    Raises:
        ValueError: If either ``api_url`` or ``token`` are not provided and the
            corresponding environment variables are not set.
        ConnectionError: If the enterprise instance is unreachable.
        PermissionError: If the token is invalid, expired, or lacks admin role.
        RuntimeError: If the server is not configured for remote connections.
    """
    api_url = api_url or LIGHTLY_STUDIO_API_URL
    token = token or LIGHTLY_STUDIO_TOKEN

    if not api_url:
        raise ValueError(
            "api_url is required. Pass it explicitly or set the "
            "LIGHTLY_STUDIO_API_URL environment variable."
        )
    if not token:
        raise ValueError(
            "token is required. Pass it explicitly or set the "
            "LIGHTLY_STUDIO_TOKEN environment variable."
        )

    # Strip trailing slash.
    api_url = api_url.rstrip("/")

    engine_url = _fetch_engine_url(api_url=api_url, token=token)
    db_manager.connect(engine_url=engine_url)


def _fetch_engine_url(api_url: str, token: str) -> str:
    """Call the enterprise endpoint to exchange a token for the DB engine URL.

    Args:
        api_url: Base URL of the LightlyStudio enterprise instance.
        token: JWT bearer token.

    Returns:
        The PostgreSQL engine URL.

    Raises:
        ConnectionError: If the server is unreachable.
        PermissionError: If authentication or authorization fails.
        RuntimeError: If the server returns an unexpected error.
    """
    url = f"{api_url}{_DB_CONNECT_ENDPOINT}"

    try:
        response = requests.get(
            url=url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.ConnectionError:
        raise ConnectionError(
            f"Could not reach LightlyStudio at {api_url}. "
            "Verify the URL and that the server is running."
        ) from None
    except requests.Timeout:
        raise ConnectionError(
            f"Request to LightlyStudio at {api_url} timed out. "
            "Verify that the server is reachable and responsive."
        ) from None

    if response.status_code == http.HTTPStatus.UNAUTHORIZED:
        raise PermissionError(
            "Authentication failed — token may have expired. Re-copy it from the LightlyStudio GUI."
        )
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
        return response.json()["engine_url"]
    except (ValueError, KeyError):
        raise RuntimeError(
            "Unexpected response from LightlyStudio: "
            "response body does not contain `engine_url`."
        ) from None
