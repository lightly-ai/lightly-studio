from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    ProviderError,
    ProviderImage,
    SegmentationPrompt,
)
from lightly_studio.services.assisted_labeling_service import segment_and_report
from lightly_studio.usage import usage_reporter

IMAGE = ProviderImage(
    sample_id=UUID("00000000-0000-0000-0000-000000000002"),
    width=100,
    height=80,
    file_name="img.png",
    read_bytes=lambda: b"",
)
COLLECTION_ID = UUID("00000000-0000-0000-0000-000000000001")
TWO_BOXES = SegmentationPrompt(
    points=[],
    boxes=[
        BoxPrompt(x_min=10, y_min=10, x_max=40, y_max=40),
        BoxPrompt(x_min=50, y_min=20, x_max=90, y_max=70),
    ],
    text=None,
    max_masks=2,
)


def test_segment_and_report__reports_a_successful_call(mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)

    predictions, latency_ms = segment_and_report.segment_and_report(
        provider=FakeProvider(),
        image=IMAGE,
        prompt=TWO_BOXES,
        operation=segment_and_report.OPERATION_INSTANCES,
        collection_id=COLLECTION_ID,
        user_email="ada@example.com",
    )

    assert len(predictions) == 2
    assert len(reported) == 1
    event = reported[0]
    assert event.user_email == "ada@example.com"
    assert event.service is usage_reporter.UsageService.AUTOLABELING
    assert event.operation == "segment_instances"
    assert event.mode is usage_reporter.UsageMode.REALTIME
    assert event.job_id is None
    assert event.vendor == "fake"
    assert event.model == "fake"
    assert event.unit is usage_reporter.UsageUnit.REQUEST
    assert event.quantity == 1
    assert event.success is True
    assert event.collection_id == COLLECTION_ID
    assert event.latency_ms == latency_ms
    assert event.details == {
        "sample_id": "00000000-0000-0000-0000-000000000002",
        "num_predictions": 2,
        "provider_id": "fake",
    }
    assert event.occurred_at.tzinfo is not None


def test_segment_and_report__reports_a_failed_call_and_reraises(mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)
    provider = FakeProvider()
    mocker.patch.object(provider, "segment", side_effect=ProviderError("provider is down"))

    with pytest.raises(ProviderError, match="provider is down"):
        segment_and_report.segment_and_report(
            provider=provider,
            image=IMAGE,
            prompt=TWO_BOXES,
            operation=segment_and_report.OPERATION_INTERACTIVE,
            collection_id=COLLECTION_ID,
            user_email=None,
        )

    assert len(reported) == 1
    event = reported[0]
    assert event.success is False
    assert event.quantity == 1
    assert event.operation == "segment_interactive"
    assert event.details is not None
    assert event.details["num_predictions"] == 0
    assert event.user_email is None


def test_segment_and_report__uses_a_new_event_id_per_call(mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)

    for _ in range(2):
        segment_and_report.segment_and_report(
            provider=FakeProvider(),
            image=IMAGE,
            prompt=TWO_BOXES,
            operation=segment_and_report.OPERATION_INSTANCES,
            collection_id=COLLECTION_ID,
            user_email=None,
        )

    assert reported[0].event_id != reported[1].event_id


def _capture_reports(mocker: MockerFixture) -> list[usage_reporter.UsageEvent]:
    reported: list[usage_reporter.UsageEvent] = []

    def _record(events: Sequence[usage_reporter.UsageEvent]) -> None:
        reported.extend(events)

    mocker.patch.object(usage_reporter, "report", side_effect=_record)
    return reported
