"""HTTP client for the fal.ai queue and storage APIs.

The storage endpoints are not documented publicly. They follow the `fal-client` package.
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Callable

import requests

from lightly_studio.assisted_labeling.provider import ProviderError

logger = logging.getLogger(__name__)

QUEUE_BASE_URL = "https://queue.fal.run"
CDN_TOKEN_URL = "https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
GCS_INITIATE_URL = "https://rest.fal.ai/storage/upload/initiate?storage_type=gcs"
REQUEST_TIMEOUT_S = 30.0
TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_DEFAULT_CONTENT_TYPE = "image/jpeg"
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


@dataclass(frozen=True)
class _CdnToken:
    authorization: str
    base_url: str
    expires_at: datetime | None


class FalUploader:
    """Uploads files to fal.ai storage and returns URLs that fal.ai models can read.

    Tries the fal CDN first, then a GCS signed upload. If both fail, returns a base64
    data URI.
    """

    def __init__(self, session: requests.Session) -> None:
        """Creates an uploader that sends requests through the session."""
        self._session = session
        self._token: _CdnToken | None = None
        self._token_lock = threading.Lock()

    def upload(self, fal_key: str, file_name: str, data: bytes) -> str:
        """Uploads the file and returns its URL.

        Args:
            fal_key: The fal.ai API key.
            file_name: File name that sets the content type and the stored name.
            data: The file content.

        Returns:
            A URL or a data URI of the file.
        """
        content_type = content_type_for(file_name=file_name)
        uploads: list[tuple[str, Callable[[str, str, str, bytes], str]]] = [
            ("fal CDN", self._upload_to_cdn),
            ("GCS", self._upload_to_gcs),
        ]
        for path_name, upload_fn in uploads:
            try:
                url = upload_fn(fal_key, file_name, content_type, data)
            except ProviderError as error:
                logger.warning("fal.ai upload of %s via %s failed: %s", file_name, path_name, error)
                continue
            logger.info("Uploaded %s to fal.ai via %s.", file_name, path_name)
            return url
        logger.warning("Sending %s to fal.ai as a base64 data URI.", file_name)
        return to_data_uri(data=data, content_type=content_type)

    def _upload_to_cdn(self, fal_key: str, file_name: str, content_type: str, data: bytes) -> str:
        token = self._get_cdn_token(fal_key=fal_key)
        output = request_json(
            session=self._session,
            method="POST",
            url=f"{token.base_url}/files/upload",
            headers={
                "Authorization": token.authorization,
                "Content-Type": content_type,
                "X-Fal-File-Name": file_name,
            },
            body=data,
        )
        return _get_str(output=output, key="access_url")

    def _upload_to_gcs(self, fal_key: str, file_name: str, content_type: str, data: bytes) -> str:
        output = request_json(
            session=self._session,
            method="POST",
            url=GCS_INITIATE_URL,
            headers=key_headers(fal_key=fal_key),
            body={"file_name": file_name, "content_type": content_type},
        )
        upload_url = _get_str(output=output, key="upload_url")
        file_url = _get_str(output=output, key="file_url")
        _send(
            session=self._session,
            method="PUT",
            url=upload_url,
            headers={"Content-Type": content_type},
            body=data,
        )
        return file_url

    def _get_cdn_token(self, fal_key: str) -> _CdnToken:
        with self._token_lock:
            now = datetime.now(timezone.utc)
            token = self._token
            if (
                token is not None
                and token.expires_at is not None
                and now < token.expires_at - TOKEN_EXPIRY_MARGIN
            ):
                return token
            output = request_json(
                session=self._session,
                method="POST",
                url=CDN_TOKEN_URL,
                headers=key_headers(fal_key=fal_key),
                body={},
            )
            token_type = _get_str(output=output, key="token_type")
            self._token = _CdnToken(
                authorization=f"{token_type} {_get_str(output=output, key='token')}",
                base_url=_get_str(output=output, key="base_url").rstrip("/"),
                expires_at=_parse_datetime(value=output.get("expires_at")),
            )
            return self._token


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
    response = _send(session=session, method=method, url=url, headers=headers, body=body)
    try:
        output = response.json()
    except ValueError as error:
        raise ProviderError(f"fal.ai returned invalid JSON for {method} {url}.") from error
    if not isinstance(output, dict):
        raise ProviderError(f"fal.ai returned unexpected JSON for {method} {url}: {output!r}")
    return output


def key_headers(fal_key: str) -> dict[str, str]:
    """Returns the headers that authenticate with a fal.ai API key."""
    return {"Authorization": f"Key {fal_key}"}


def content_type_for(file_name: str) -> str:
    """Returns the image content type for the file extension. The default is JPEG."""
    return _CONTENT_TYPES.get(PurePosixPath(file_name).suffix.lower(), _DEFAULT_CONTENT_TYPE)


def to_data_uri(data: bytes, content_type: str) -> str:
    """Returns the data as a base64 data URI."""
    return f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"


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


def _send(
    session: requests.Session,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | bytes | None = None,
) -> requests.Response:
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


def _get_str(output: dict[str, Any], key: str) -> str:
    value = output.get(key)
    if not isinstance(value, str) or not value:
        raise ProviderError(f"fal.ai response has no '{key}': {output!r}")
    return value


def _parse_datetime(value: object) -> datetime | None:
    """Parses an ISO 8601 time. Returns None if the value is not a valid time."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
