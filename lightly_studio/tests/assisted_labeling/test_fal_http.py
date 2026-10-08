from __future__ import annotations

from typing import cast

import pytest
import requests
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import fal_http
from lightly_studio.assisted_labeling.provider import ProviderError
from tests.assisted_labeling.helpers import FakeResponse, FakeSession

STATUS_URL = "https://queue.fal.run/fal-ai/x/requests/1/status"
RESPONSE_URL = "https://queue.fal.run/fal-ai/x/requests/1"
SUBMIT_URL = "https://queue.fal.run/fal-ai/x"
CDN_BASE_URL = "https://v3.fal.media"
CDN_UPLOAD_URL = "https://v3.fal.media/files/upload"
GCS_UPLOAD_URL = "https://storage.googleapis.com/signed"
SUBMITTED = {"request_id": "1", "status_url": STATUS_URL, "response_url": RESPONSE_URL}
TOKEN = {
    "token": "tok",
    "token_type": "Bearer",
    "base_url": CDN_BASE_URL,
    "expires_at": "2999-01-01T00:00:00Z",
}


def _as_session(session: FakeSession) -> requests.Session:
    return cast(requests.Session, session)


class TestFalUploader:
    def test_upload__cdn(self) -> None:
        session = FakeSession(
            responses={
                ("POST", fal_http.CDN_TOKEN_URL): [FakeResponse(json_body=TOKEN)],
                ("POST", CDN_UPLOAD_URL): [
                    FakeResponse(json_body={"access_url": "https://v3.fal.media/files/a.png"})
                ],
            }
        )
        uploader = fal_http.FalUploader(session=_as_session(session))

        url = uploader.upload(fal_key="secret", file_name="a.png", data=b"data")

        assert url == "https://v3.fal.media/files/a.png"
        token_call = session.calls_to(method="POST", url=fal_http.CDN_TOKEN_URL)[0]
        assert token_call["headers"] == {"Authorization": "Key secret"}
        assert token_call["json"] == {}
        upload_call = session.calls_to(method="POST", url=CDN_UPLOAD_URL)[0]
        assert upload_call["headers"] == {
            "Authorization": "Bearer tok",
            "Content-Type": "image/png",
            "X-Fal-File-Name": "a.png",
        }
        assert upload_call["data"] == b"data"

    def test_upload__caches_token(self) -> None:
        session = FakeSession(
            responses={
                ("POST", fal_http.CDN_TOKEN_URL): [FakeResponse(json_body=TOKEN)],
                ("POST", CDN_UPLOAD_URL): [FakeResponse(json_body={"access_url": "url"})],
            }
        )
        uploader = fal_http.FalUploader(session=_as_session(session))

        uploader.upload(fal_key="secret", file_name="a.jpg", data=b"1")
        uploader.upload(fal_key="secret", file_name="b.jpg", data=b"2")

        assert len(session.calls_to(method="POST", url=fal_http.CDN_TOKEN_URL)) == 1
        assert len(session.calls_to(method="POST", url=CDN_UPLOAD_URL)) == 2

    def test_upload__refreshes_expired_token(self) -> None:
        expired_token = {**TOKEN, "expires_at": "2000-01-01T00:00:00Z"}
        session = FakeSession(
            responses={
                ("POST", fal_http.CDN_TOKEN_URL): [FakeResponse(json_body=expired_token)],
                ("POST", CDN_UPLOAD_URL): [FakeResponse(json_body={"access_url": "url"})],
            }
        )
        uploader = fal_http.FalUploader(session=_as_session(session))

        uploader.upload(fal_key="secret", file_name="a.jpg", data=b"1")
        uploader.upload(fal_key="secret", file_name="b.jpg", data=b"2")

        assert len(session.calls_to(method="POST", url=fal_http.CDN_TOKEN_URL)) == 2

    def test_upload__gcs_fallback(self) -> None:
        session = FakeSession(
            responses={
                ("POST", fal_http.CDN_TOKEN_URL): [FakeResponse(status_code=500)],
                ("POST", fal_http.GCS_INITIATE_URL): [
                    FakeResponse(
                        json_body={"upload_url": GCS_UPLOAD_URL, "file_url": "https://file"}
                    )
                ],
                ("PUT", GCS_UPLOAD_URL): [FakeResponse()],
            }
        )
        uploader = fal_http.FalUploader(session=_as_session(session))

        url = uploader.upload(fal_key="secret", file_name="a.webp", data=b"data")

        assert url == "https://file"
        initiate_call = session.calls_to(method="POST", url=fal_http.GCS_INITIATE_URL)[0]
        assert initiate_call["json"] == {"file_name": "a.webp", "content_type": "image/webp"}
        assert initiate_call["headers"] == {"Authorization": "Key secret"}
        put_call = session.calls_to(method="PUT", url=GCS_UPLOAD_URL)[0]
        assert put_call["data"] == b"data"
        assert put_call["headers"] == {"Content-Type": "image/webp"}

    def test_upload__data_uri_fallback(self) -> None:
        session = FakeSession(
            responses={
                ("POST", fal_http.CDN_TOKEN_URL): [FakeResponse(status_code=500)],
                ("POST", fal_http.GCS_INITIATE_URL): [FakeResponse(status_code=403)],
            }
        )
        uploader = fal_http.FalUploader(session=_as_session(session))

        url = uploader.upload(fal_key="secret", file_name="a.jpg", data=b"abc")

        assert url == "data:image/jpeg;base64,YWJj"


def test_run_queue_request() -> None:
    session = FakeSession(
        responses={
            ("POST", SUBMIT_URL): [FakeResponse(json_body=SUBMITTED)],
            ("GET", STATUS_URL): [
                FakeResponse(json_body={"status": "IN_QUEUE"}),
                FakeResponse(json_body={"status": "IN_PROGRESS"}),
                FakeResponse(json_body={"status": "COMPLETED"}),
            ],
            ("GET", RESPONSE_URL): [FakeResponse(json_body={"rle": "0 1"})],
        }
    )

    output = fal_http.run_queue_request(
        session=_as_session(session),
        fal_key="secret",
        endpoint="fal-ai/x",
        body={"image_url": "url"},
        polling=fal_http.PollingConfig(timeout_s=10.0, interval_s=0.0),
    )

    assert output == {"rle": "0 1"}
    submit_call = session.calls_to(method="POST", url=SUBMIT_URL)[0]
    assert submit_call["json"] == {"image_url": "url"}
    assert submit_call["headers"] == {"Authorization": "Key secret"}
    assert len(session.calls_to(method="GET", url=STATUS_URL)) == 3


def test_run_queue_request__http_error() -> None:
    session = FakeSession(
        responses={("POST", SUBMIT_URL): [FakeResponse(json_body="Unauthorized", status_code=401)]}
    )

    with pytest.raises(ProviderError, match="failed with status 401: Unauthorized"):
        fal_http.run_queue_request(
            session=_as_session(session),
            fal_key="secret",
            endpoint="fal-ai/x",
            body={},
            polling=fal_http.PollingConfig(timeout_s=10.0, interval_s=0.0),
        )


def test_run_queue_request__error_status() -> None:
    session = FakeSession(
        responses={
            ("POST", SUBMIT_URL): [FakeResponse(json_body=SUBMITTED)],
            ("GET", STATUS_URL): [FakeResponse(json_body={"status": "COMPLETED", "error": "boom"})],
        }
    )

    with pytest.raises(ProviderError, match=r"fal\.ai request failed: boom"):
        fal_http.run_queue_request(
            session=_as_session(session),
            fal_key="secret",
            endpoint="fal-ai/x",
            body={},
            polling=fal_http.PollingConfig(timeout_s=10.0, interval_s=0.0),
        )


def test_run_queue_request__timeout() -> None:
    session = FakeSession(
        responses={
            ("POST", SUBMIT_URL): [FakeResponse(json_body=SUBMITTED)],
            ("GET", STATUS_URL): [FakeResponse(json_body={"status": "IN_QUEUE"})],
        }
    )

    with pytest.raises(ProviderError, match=r"did not complete within 0\.0 s"):
        fal_http.run_queue_request(
            session=_as_session(session),
            fal_key="secret",
            endpoint="fal-ai/x",
            body={},
            polling=fal_http.PollingConfig(timeout_s=0.0, interval_s=0.0),
        )


def test_run_queue_request__connection_error(mocker: MockerFixture) -> None:
    session = mocker.MagicMock(spec=requests.Session)
    session.request.side_effect = requests.ConnectionError("offline")

    with pytest.raises(ProviderError, match="offline"):
        fal_http.run_queue_request(
            session=session,
            fal_key="secret",
            endpoint="fal-ai/x",
            body={},
            polling=fal_http.PollingConfig(timeout_s=10.0, interval_s=0.0),
        )


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("a.jpg", "image/jpeg"),
        ("a.JPEG", "image/jpeg"),
        ("dir/a.png", "image/png"),
        ("a.webp", "image/webp"),
        ("a.bmp", "image/jpeg"),
        ("a", "image/jpeg"),
    ],
)
def test_content_type_for(file_name: str, expected: str) -> None:
    assert fal_http.content_type_for(file_name=file_name) == expected
