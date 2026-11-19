"""Requests to the v1 REST API of the Studio backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

API_PREFIX = "/api/v1"


def get(client: httpx.Client, path: str, params: Mapping[str, Any] | None = None) -> Any:
    """Send a GET request to a v1 path and return the JSON body.

    Return None if the backend reports that the resource does not exist. The `path` has no
    query string, give the query in `params`.

    Raises:
        ValueError: If the server rejects the request with status 400 or 422.
    """
    query = {key: value for key, value in (params or {}).items() if value is not None}
    response = client.get(API_PREFIX + path, params=query)
    if _is_resource_not_found(response=response):
        return None
    _check_status(response=response)
    return response.json()


def post(client: httpx.Client, path: str, body: Any) -> Any:
    """Send a POST request to a v1 path and return the JSON body, or None if it is empty.

    Raises:
        ValueError: If the server rejects the request with status 400 or 422.
    """
    response = client.post(API_PREFIX + path, json=body)
    _check_status(response=response)
    return None if response.status_code == httpx.codes.NO_CONTENT else response.json()


def _check_status(response: httpx.Response) -> None:
    if response.status_code in (httpx.codes.BAD_REQUEST, httpx.codes.UNPROCESSABLE_ENTITY):
        raise ValueError(_error_message(response=response))
    response.raise_for_status()


def _is_resource_not_found(response: httpx.Response) -> bool:
    # The 404 of an unknown route has no `error` key, the `NotFoundError` handler adds it.
    if response.status_code != httpx.codes.NOT_FOUND:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    return isinstance(body, dict) and "error" in body


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict):
        return str(body.get("error") or body.get("detail") or body)
    return str(body)
