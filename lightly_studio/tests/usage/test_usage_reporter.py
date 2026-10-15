from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
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
    session = mocker.patch.object(usage_reporter, "_session")
    mocker.patch.object(env, "LIGHTLY_STUDIO_USAGE_REPORT_URL", url)
    mocker.patch.object(env, "LIGHTLY_STUDIO_CONTROL_PLANE_TOKEN", token)

    usage_reporter.report(events=[EVENT])

    session.post.assert_not_called()


def test_report__sends_with_config(mocker: MockerFixture) -> None:
    session = mocker.patch.object(usage_reporter, "_session")
    mocker.patch.object(env, "LIGHTLY_STUDIO_USAGE_REPORT_URL", URL)
    mocker.patch.object(env, "LIGHTLY_STUDIO_CONTROL_PLANE_TOKEN", "t0k")

    usage_reporter.report(events=[EVENT])

    session.post.assert_called_once()
    assert session.post.call_args.args == (URL,)


def test_send__posts_the_events_with_the_token(mocker: MockerFixture) -> None:
    session = mocker.Mock()

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session)

    session.post.assert_called_once_with(
        URL,
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
    session = mocker.Mock()
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


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(requests.ConnectionError("down"), id="connection-error"),
        pytest.param(requests.HTTPError("500", response=requests.Response()), id="error-status"),
        pytest.param(ValueError("boom"), id="non-requests-error"),
    ],
)
def test_send__never_raises(mocker: MockerFixture, error: Exception) -> None:
    session = mocker.Mock()
    session.post.return_value.raise_for_status.side_effect = error

    usage_reporter.send(events=[EVENT], url=URL, token="t0k", session=session)

    session.post.assert_called_once()
