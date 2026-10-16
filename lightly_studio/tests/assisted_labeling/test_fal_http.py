from __future__ import annotations

from typing import Any

import pytest
import requests
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import fal_http
from lightly_studio.assisted_labeling.fal_http import PollingConfig
from lightly_studio.assisted_labeling.provider import ProviderError

from .helpers import FakeResponse, FakeSession

ENDPOINT = "fal-ai/test"
SUBMIT_URL = f"{fal_http.QUEUE_BASE_URL}/{ENDPOINT}"
STATUS_URL = "https://queue.fal.run/status"
RESPONSE_URL = "https://queue.fal.run/response"
SUBMITTED = {"status_url": STATUS_URL, "response_url": RESPONSE_URL}
FAST_POLLING = PollingConfig(timeout_s=5.0, interval_s=0.0)


def _run(session: FakeSession, polling: PollingConfig = FAST_POLLING) -> dict[str, Any]:
    return fal_http.run_queue_request(
        session=session,  # type: ignore[arg-type]
        fal_key="secret",
        endpoint=ENDPOINT,
        body={"a": 1},
        polling=polling,
    )


def _queue_session(status_responses: list[FakeResponse]) -> FakeSession:
    return FakeSession(
        {
            ("POST", SUBMIT_URL): [FakeResponse(SUBMITTED)],
            ("GET", STATUS_URL): status_responses,
            ("GET", RESPONSE_URL): [FakeResponse({"masks": []})],
        }
    )


def test_run_queue_request__submit_poll_fetch(mocker: MockerFixture) -> None:
    mocker.patch("time.sleep")
    session = _queue_session(
        [FakeResponse({"status": "IN_QUEUE"}), FakeResponse({"status": "COMPLETED"})]
    )

    output = _run(session)

    assert output == {"masks": []}
    assert [(call["method"], call["url"]) for call in session.calls] == [
        ("POST", SUBMIT_URL),
        ("GET", STATUS_URL),
        ("GET", STATUS_URL),
        ("GET", RESPONSE_URL),
    ]
    assert session.calls[0]["json"] == {"a": 1}
    assert all(call["headers"] == {"Authorization": "Key secret"} for call in session.calls)


def test_run_queue_request__completed_with_error() -> None:
    session = _queue_session([FakeResponse({"status": "COMPLETED", "error": "boom"})])

    with pytest.raises(ProviderError, match="boom"):
        _run(session)


def test_run_queue_request__unknown_status() -> None:
    session = _queue_session([FakeResponse({"status": "WEIRD"})])

    with pytest.raises(ProviderError, match="unexpected status"):
        _run(session)


def test_run_queue_request__timeout(mocker: MockerFixture) -> None:
    sleep = mocker.patch("time.sleep")
    session = _queue_session([FakeResponse({"status": "IN_PROGRESS"})])

    with pytest.raises(ProviderError, match="did not complete"):
        _run(session, polling=PollingConfig(timeout_s=0, interval_s=0))

    sleep.assert_not_called()


def test_run_queue_request__missing_status_url() -> None:
    session = FakeSession({("POST", SUBMIT_URL): [FakeResponse({})]})

    with pytest.raises(ProviderError, match="status_url"):
        _run(session)


def test_request_json__non_ok_status_in_message() -> None:
    session = FakeSession({("GET", STATUS_URL): [FakeResponse({"detail": "no"}, status_code=503)]})

    with pytest.raises(ProviderError, match="503"):
        fal_http.request_json(
            session=session,  # type: ignore[arg-type]
            method="GET",
            url=STATUS_URL,
            headers={},
        )


def test_request_json__invalid_json() -> None:
    session = FakeSession({("GET", STATUS_URL): [FakeResponse(ValueError("bad"))]})

    with pytest.raises(ProviderError, match="invalid JSON"):
        fal_http.request_json(
            session=session,  # type: ignore[arg-type]
            method="GET",
            url=STATUS_URL,
            headers={},
        )


def test_request_json__non_dict_json() -> None:
    session = FakeSession({("GET", STATUS_URL): [FakeResponse([1, 2])]})

    with pytest.raises(ProviderError, match="unexpected JSON"):
        fal_http.request_json(
            session=session,  # type: ignore[arg-type]
            method="GET",
            url=STATUS_URL,
            headers={},
        )


def test_send__request_exception(mocker: MockerFixture) -> None:
    session = mocker.Mock()
    session.request.side_effect = requests.ConnectionError("down")

    with pytest.raises(ProviderError, match="down"):
        fal_http.send(session=session, method="GET", url=STATUS_URL, headers={})
