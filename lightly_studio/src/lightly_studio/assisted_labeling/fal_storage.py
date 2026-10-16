"""Image upload to the fal.ai CDN.

The storage endpoints are not documented publicly. They follow the `fal-client` package.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Callable

import requests

from lightly_studio.assisted_labeling import fal_http

CDN_TOKEN_URL = "https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_DEFAULT_CONTENT_TYPE = "image/jpeg"


@dataclass(frozen=True)
class _CdnToken:
    authorization: str
    base_url: str
    expires_at: datetime | None


class FalUploader:
    """Uploads files to the fal.ai CDN and returns URLs that fal.ai models can read."""

    def __init__(
        self,
        session: requests.Session,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Creates an uploader that sends requests through the session.

        Args:
            session: HTTP session for the requests.
            now: Returns the current time. Replaceable in tests.
        """
        self._session = session
        self._now = now
        self._token: _CdnToken | None = None
        self._token_lock = threading.Lock()

    def upload(self, fal_key: str, file_name: str, data: bytes) -> str:
        """Uploads the file and returns its URL.

        Args:
            fal_key: The fal.ai API key.
            file_name: File name that sets the content type and the stored name.
            data: The file content.

        Returns:
            The URL of the uploaded file.

        Raises:
            ProviderError: If the token request or the upload fails.
        """
        token = self._get_cdn_token(fal_key=fal_key)
        output = fal_http.request_json(
            session=self._session,
            method="POST",
            url=f"{token.base_url}/files/upload",
            headers={
                "Authorization": token.authorization,
                "Content-Type": content_type_for(file_name=file_name),
                "X-Fal-File-Name": file_name,
            },
            body=data,
        )
        return fal_http.get_str(output=output, key="access_url")

    def _get_cdn_token(self, fal_key: str) -> _CdnToken:
        with self._token_lock:
            token = self._token
            if (
                token is not None
                and token.expires_at is not None
                and self._now() < token.expires_at - TOKEN_EXPIRY_MARGIN
            ):
                return token
            output = fal_http.request_json(
                session=self._session,
                method="POST",
                url=CDN_TOKEN_URL,
                headers=fal_http.key_headers(fal_key=fal_key),
                body={},
            )
            token_type = fal_http.get_str(output=output, key="token_type")
            self._token = _CdnToken(
                authorization=f"{token_type} {fal_http.get_str(output=output, key='token')}",
                base_url=fal_http.get_str(output=output, key="base_url").rstrip("/"),
                expires_at=_parse_datetime(value=output.get("expires_at")),
            )
            return self._token


def content_type_for(file_name: str) -> str:
    """Returns the image content type for the file extension. The default is JPEG."""
    return _CONTENT_TYPES.get(PurePosixPath(file_name).suffix.lower(), _DEFAULT_CONTENT_TYPE)


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
