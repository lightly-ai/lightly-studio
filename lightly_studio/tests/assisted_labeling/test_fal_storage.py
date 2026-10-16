from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lightly_studio.assisted_labeling import fal_storage
from lightly_studio.assisted_labeling.fal_storage import FalUploader
from lightly_studio.assisted_labeling.provider import ProviderError

from .helpers import FakeResponse, FakeSession

CDN_BASE_URL = "https://v3.fal.media"
UPLOAD_URL = f"{CDN_BASE_URL}/files/upload"
TOKEN_KEY = ("POST", fal_storage.CDN_TOKEN_URL)
UPLOAD_KEY = ("POST", UPLOAD_URL)
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _Clock:
    def __init__(self) -> None:
        self.current = START

    def __call__(self) -> datetime:
        return self.current


def _token_response(expires_at: datetime | None = START + timedelta(hours=1)) -> FakeResponse:
    body = {"token": "cdn-token", "token_type": "Bearer", "base_url": f"{CDN_BASE_URL}/"}
    if expires_at is not None:
        body["expires_at"] = expires_at.isoformat()
    return FakeResponse(body)


def _uploader(session: FakeSession, clock: _Clock | None = None) -> FalUploader:
    return FalUploader(session=session, now=clock or _Clock())  # type: ignore[arg-type]


def test_upload__returns_access_url_and_sends_headers() -> None:
    session = FakeSession(
        {
            TOKEN_KEY: [_token_response()],
            UPLOAD_KEY: [FakeResponse({"access_url": "https://cdn/a"})],
        }
    )

    url = _uploader(session).upload(fal_key="secret", file_name="photo.png", data=b"bytes")

    assert url == "https://cdn/a"
    (token_call,) = session.calls_to(*TOKEN_KEY)
    assert token_call["headers"] == {"Authorization": "Key secret"}
    (upload_call,) = session.calls_to(*UPLOAD_KEY)
    assert upload_call["data"] == b"bytes"
    assert upload_call["headers"] == {
        "Authorization": "Bearer cdn-token",
        "Content-Type": "image/png",
        "X-Fal-File-Name": "photo.png",
    }


def test_upload__upload_failure_raises_provider_error() -> None:
    session = FakeSession(
        {TOKEN_KEY: [_token_response()], UPLOAD_KEY: [FakeResponse({}, status_code=500)]}
    )

    with pytest.raises(ProviderError, match="status 500"):
        _uploader(session).upload(fal_key="secret", file_name="a.jpg", data=b"")


def test_upload__token_failure_raises_provider_error() -> None:
    session = FakeSession({TOKEN_KEY: [FakeResponse({}, status_code=401)]})

    with pytest.raises(ProviderError, match="status 401"):
        _uploader(session).upload(fal_key="secret", file_name="a.jpg", data=b"")


def test_upload__missing_access_url_raises_provider_error() -> None:
    session = FakeSession({TOKEN_KEY: [_token_response()], UPLOAD_KEY: [FakeResponse({})]})

    with pytest.raises(ProviderError, match="access_url"):
        _uploader(session).upload(fal_key="secret", file_name="a.jpg", data=b"")


def test_upload__reuses_token_before_expiry() -> None:
    clock = _Clock()
    session = FakeSession(
        {TOKEN_KEY: [_token_response()], UPLOAD_KEY: [FakeResponse({"access_url": "u"})]}
    )
    uploader = _uploader(session, clock)

    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")
    clock.current = START + timedelta(minutes=58)
    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")

    assert len(session.calls_to(*TOKEN_KEY)) == 1
    assert len(session.calls_to(*UPLOAD_KEY)) == 2


def test_upload__refreshes_token_within_margin_of_expiry() -> None:
    clock = _Clock()
    session = FakeSession(
        {TOKEN_KEY: [_token_response()], UPLOAD_KEY: [FakeResponse({"access_url": "u"})]}
    )
    uploader = _uploader(session, clock)

    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")
    clock.current = START + timedelta(minutes=59, seconds=1)
    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")

    assert len(session.calls_to(*TOKEN_KEY)) == 2


def test_upload__token_without_expiry_is_not_cached() -> None:
    session = FakeSession(
        {
            TOKEN_KEY: [_token_response(expires_at=None)],
            UPLOAD_KEY: [FakeResponse({"access_url": "u"})],
        }
    )
    uploader = _uploader(session)

    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")
    uploader.upload(fal_key="secret", file_name="a.jpg", data=b"")

    assert len(session.calls_to(*TOKEN_KEY)) == 2


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("a.jpg", "image/jpeg"),
        ("a.JPEG", "image/jpeg"),
        ("a.png", "image/png"),
        ("a.webp", "image/webp"),
        ("a.bmp", "image/jpeg"),
        ("a", "image/jpeg"),
    ],
)
def test_content_type_for(file_name: str, expected: str) -> None:
    assert fal_storage.content_type_for(file_name=file_name) == expected


def test_parse_datetime__invalid_values_return_none() -> None:
    assert fal_storage._parse_datetime(value=None) is None
    assert fal_storage._parse_datetime(value="not a time") is None


def test_parse_datetime__naive_time_is_utc() -> None:
    parsed = fal_storage._parse_datetime(value="2026-01-01T00:00:00")

    assert parsed == START
