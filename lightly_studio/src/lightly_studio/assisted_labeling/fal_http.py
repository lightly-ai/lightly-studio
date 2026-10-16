"""HTTP client for the fal.ai queue API.

Sync on purpose: routes run it on a bounded executor.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from lightly_studio.assisted_labeling.provider import ProviderError

QUEUE_BASE_URL = "https://queue.fal.run"
REQUEST_TIMEOUT_S = 30.0

_PENDING_STATUSES = {"IN_QUEUE", "IN_PROGRESS"}


@dataclass(frozen=True)
class PollingConfig:
    """Timing of the queue status requests.

    Attributes:
        timeout_s: Maximum time to wait for a result, in seconds.
        interval_s: Time between status requests, in seconds.
    """

    timeout_s: float = 60.0
    interval_s: float = 0.15


def run_queue_request(
    session: requests.Session,
    fal_key: str,
    endpoint: str,
    body: dict[str, Any],
    polling: PollingConfig,
) -> dict[str, Any]:
    """Submits a request to the fal.ai queue, waits for it, and returns its output.

    Args:
        session: HTTP session for the requests.
        fal_key: The fal.ai API key.
        endpoint: Model endpoint, for example `fal-ai/sam-3/image-rle`.
        body: JSON input of the model.
        polling: Timing of the status requests.

    Returns:
        The JSON output of the model.

    Raises:
        ProviderError: If a request fails, the request fails on fal.ai, or the timeout
            expires.
    """
    headers = key_headers(fal_key=fal_key)
    submitted = request_json(
        session=session,
        method="POST",
        url=f"{QUEUE_BASE_URL}/{endpoint}",
        headers=headers,
        body=body,
    )
    _wait_for_completion(
        session=session,
        headers=headers,
        status_url=_get_str(output=submitted, key="status_url"),
        polling=polling,
    )
    return request_json(
        session=session,
        method="GET",
        url=_get_str(output=submitted, key="response_url"),
        headers=headers,
    )


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | bytes | None = None,
) -> dict[str, Any]:
    """Sends a request and returns the JSON object of the response.

    Args:
        session: HTTP session for the request.
        method: HTTP method.
        url: Request URL.
        headers: Request headers.
        body: A dict is sent as JSON, bytes are sent as they are.

    Raises:
        ProviderError: If the request fails or the response is not a JSON object.
    """
    response = send(session=session, method=method, url=url, headers=headers, body=body)
    try:
        output = response.json()
    except ValueError as error:
        raise ProviderError(f"fal.ai returned invalid JSON for {method} {url}.") from error
    if not isinstance(output, dict):
        raise ProviderError(f"fal.ai returned unexpected JSON for {method} {url}: {output!r}")
    return output


def send(
    session: requests.Session,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | bytes | None = None,
) -> requests.Response:
    """Sends a request and returns the response.

    Raises:
        ProviderError: If the request fails or the status is not OK.
    """
    try:
        response = session.request(
            method=method,
            url=url,
            headers=headers,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, bytes) else None,
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as error:
        raise ProviderError(f"fal.ai request {method} {url} failed: {error}") from error
    if not response.ok:
        raise ProviderError(
            f"fal.ai request {method} {url} failed with status {response.status_code}: "
            f"{response.text[:500]}"
        )
    return response


def key_headers(fal_key: str) -> dict[str, str]:
    """Returns the headers that authenticate with a fal.ai API key."""
    return {"Authorization": f"Key {fal_key}"}


def _wait_for_completion(
    session: requests.Session,
    headers: dict[str, str],
    status_url: str,
    polling: PollingConfig,
) -> None:
    deadline = time.monotonic() + polling.timeout_s
    while True:
        status_output = request_json(session=session, method="GET", url=status_url, headers=headers)
        status = status_output.get("status")
        if status == "COMPLETED":
            if status_output.get("error"):
                raise ProviderError(f"fal.ai request failed: {status_output['error']}")
            return
        if status not in _PENDING_STATUSES:
            raise ProviderError(f"fal.ai request has unexpected status: {status_output!r}")
        if time.monotonic() >= deadline:
            raise ProviderError(f"fal.ai request did not complete within {polling.timeout_s} s.")
        time.sleep(polling.interval_s)


def _get_str(output: dict[str, Any], key: str) -> str:
    value = output.get(key)
    if not isinstance(value, str) or not value:
        raise ProviderError(f"fal.ai response has no '{key}': {output!r}")
    return value
