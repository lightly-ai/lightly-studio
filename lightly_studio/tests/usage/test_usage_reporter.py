from __future__ import annotations

import dataclasses
import queue
import threading
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest
import requests
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.usage import usage_reporter

EVENT = usage_reporter.UsageEvent(
    event_id=UUID("00000000-0000-0000-0000-0000000000aa"),
    occurred_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
    user_email="ada@example.com",
    service=usage_reporter.UsageService.AUTOLABELING,
    operation="segment_instances",
    mode=usage_reporter.UsageMode.REALTIME,
    vendor="fal",
    model="fal-ai/sam-3/image-rle",
    unit=usage_reporter.UsageUnit.REQUEST,
    quantity=1,
    success=True,
    collection_id=UUID("00000000-0000-0000-0000-000000000001"),
    latency_ms=950.0,
    details={"sample_id": "00000000-0000-0000-0000-000000000002", "num_predictions": 3},
)
URL = "https://cp.example/usage-events"


@pytest.mark.parametrize(
    ("url", "token"),
    [
        (None, "t0k"),
        (URL, None),
        ("", "t0k"),
        (URL, ""),
    ],
    ids=["no-url", "no-token", "empty-url", "empty-token"],
)
def test_report__does_nothing_without_config(
    mocker: MockerFixture, url: str | None, token: str | None
) -> None:
    event_queue = _patch_queue(mocker=mocker)
    start_worker = mocker.patch.object(usage_reporter, "_start_worker")
    mocker.patch.object(env, "LIGHTLY_STUDIO_USAGE_REPORT_URL", url)
    mocker.patch.object(env, "LIGHTLY_STUDIO_CONTROL_PLANE_TOKEN", token)

    usage_reporter.report(events=[EVENT])

    assert event_queue.empty()
    start_worker.assert_not_called()


def test_report__sends_from_a_worker_thread(mocker: MockerFixture) -> None:
    _patch_queue(mocker=mocker)
    mocker.patch.object(usage_reporter, "_worker_started", threading.Event())
    sent = threading.Event()
    sending_threads: list[threading.Thread] = []

    def _send(**_kwargs: object) -> None:
        sending_threads.append(threading.current_thread())
        sent.set()

    send = mocker.patch.object(usage_reporter, "send", side_effect=_send)
    mocker.patch.object(env, "LIGHTLY_STUDIO_USAGE_REPORT_URL", URL)
    mocker.patch.object(env, "LIGHTLY_STUDIO_CONTROL_PLANE_TOKEN", "t0k")

    usage_reporter.report(events=[EVENT])

    assert sent.wait(timeout=5)
    assert send.call_args.kwargs["events"] == [EVENT]
    assert send.call_args.kwargs["url"] == URL
    assert send.call_args.kwargs["token"] == "t0k"
    # The caller never waits for the receiver.
    assert sending_threads[0] is not threading.current_thread()


def test_report__drops_events_when_the_queue_is_full(mocker: MockerFixture) -> None:
    event_queue = _patch_queue(mocker=mocker, maxsize=1)
    mocker.patch.object(usage_reporter, "_start_worker")
    mocker.patch.object(env, "LIGHTLY_STUDIO_USAGE_REPORT_URL", URL)
    mocker.patch.object(env, "LIGHTLY_STUDIO_CONTROL_PLANE_TOKEN", "t0k")
    second = dataclasses.replace(EVENT, event_id=UUID("00000000-0000-0000-0000-0000000000ab"))

    usage_reporter.report(events=[EVENT, second])

    assert event_queue.get_nowait() == EVENT
    assert event_queue.empty()


def test_send__posts_the_events_with_the_token(mocker: MockerFixture) -> None:
    session = _session_answering(mocker=mocker, status_codes=[204])

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session)

    session.post.assert_called_once_with(
        url=URL,
        json={
            "events": [
                {
                    "event_id": "00000000-0000-0000-0000-0000000000aa",
                    "occurred_at": "2026-08-03T12:00:00+00:00",
                    "user_email": "ada@example.com",
                    "service": "autolabeling",
                    "operation": "segment_instances",
                    "mode": "realtime",
                    "job_id": None,
                    "vendor": "fal",
                    "model": "fal-ai/sam-3/image-rle",
                    "unit": "request",
                    "quantity": 1,
                    "success": True,
                    "collection_id": "00000000-0000-0000-0000-000000000001",
                    "latency_ms": 950.0,
                    "details": {
                        "sample_id": "00000000-0000-0000-0000-000000000002",
                        "num_predictions": 3,
                    },
                }
            ]
        },
        headers={"Authorization": "Bearer t0k"},
        timeout=2.0,
    )


def test_send__serializes_a_batch_event(mocker: MockerFixture) -> None:
    session = _session_answering(mocker=mocker, status_codes=[204])
    batch_event = dataclasses.replace(
        EVENT,
        service=usage_reporter.UsageService.EMBEDDING,
        operation="embed_image",
        mode=usage_reporter.UsageMode.BATCH,
        job_id=UUID("00000000-0000-0000-0000-0000000000bb"),
        unit=usage_reporter.UsageUnit.IMAGE,
        quantity=500,
        collection_id=None,
        latency_ms=None,
        details=None,
    )

    usage_reporter.send(events=[batch_event], url=URL, token="t0k", session=session)

    sent = session.post.call_args.kwargs["json"]["events"][0]
    assert sent["mode"] == "batch"
    assert sent["job_id"] == "00000000-0000-0000-0000-0000000000bb"
    assert sent["unit"] == "image"
    assert sent["quantity"] == 500
    assert sent["collection_id"] is None
    assert sent["latency_ms"] is None
    assert sent["details"] is None


def test_send__retries_transient_failures(mocker: MockerFixture) -> None:
    session = _session_answering(mocker=mocker, status_codes=[503, 204])
    session.post.side_effect = [requests.ConnectionError("down"), *session.post.side_effect]
    sleep = mocker.Mock()

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session, sleep=sleep)

    assert session.post.call_count == 3
    assert sleep.call_args_list == [mocker.call(1.0), mocker.call(5.0)]


def test_send__gives_up_after_three_attempts(mocker: MockerFixture) -> None:
    session = _session_answering(mocker=mocker, status_codes=[500, 502, 503, 204])
    sleep = mocker.Mock()

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session, sleep=sleep)

    assert session.post.call_count == 3


@pytest.mark.parametrize("status_code", [401, 422])
def test_send__does_not_retry_a_rejected_report(mocker: MockerFixture, status_code: int) -> None:
    session = _session_answering(mocker=mocker, status_codes=[status_code, 204])
    sleep = mocker.Mock()

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session, sleep=sleep)

    session.post.assert_called_once()
    sleep.assert_not_called()


def test_send__never_raises(mocker: MockerFixture) -> None:
    session = mocker.Mock()
    session.post.side_effect = ValueError("boom")

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session)

    session.post.assert_called_once()


def test_take_events__returns_at_most_one_batch() -> None:
    event_queue: queue.Queue[usage_reporter.UsageEvent] = queue.Queue()
    for _ in range(usage_reporter.MAX_EVENTS_PER_REPORT + 1):
        event_queue.put(EVENT)

    first = usage_reporter._take_events(event_queue=event_queue)
    second = usage_reporter._take_events(event_queue=event_queue)

    assert len(first) == usage_reporter.MAX_EVENTS_PER_REPORT
    assert len(second) == 1


def _patch_queue(mocker: MockerFixture, maxsize: int = 0) -> queue.Queue[usage_reporter.UsageEvent]:
    event_queue: queue.Queue[usage_reporter.UsageEvent] = queue.Queue(maxsize=maxsize)
    mocker.patch.object(usage_reporter, "_queue", event_queue)
    return event_queue


def _session_answering(mocker: MockerFixture, status_codes: list[int]) -> Mock:
    session: Mock = mocker.Mock()
    session.post.side_effect = [mocker.Mock(status_code=code) for code in status_codes]
    return session
