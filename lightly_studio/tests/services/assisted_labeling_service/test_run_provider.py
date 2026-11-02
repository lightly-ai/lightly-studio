from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

import numpy as np
import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.provider import (
    PointPrompt,
    Prediction,
    ProviderError,
    ProviderNotCalledError,
    ProviderUnavailableError,
)
from lightly_studio.errors import NotFoundError
from lightly_studio.services.assisted_labeling_service import run_provider
from lightly_studio.usage import usage_reporter
from tests.assisted_labeling import helpers
from tests.services.assisted_labeling_service.helpers import StubProvider

PROMPT = helpers.make_prompt(points=[PointPrompt(x=50, y=25, positive=True)])
COLLECTION_ID = UUID(int=7)


def test_segment(mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    reported = _capture_reports(mocker=mocker)
    prediction = Prediction(mask=np.ones((50, 100), dtype=np.bool_), score=0.9)
    provider = StubProvider(predictions=[prediction])
    image = helpers.make_image(width=100, height=50)

    with caplog.at_level(logging.DEBUG, logger=run_provider.__name__):
        predictions = run_provider.segment(
            provider=provider,
            image=image,
            prompt=PROMPT,
            operation=run_provider.OPERATION_INTERACTIVE,
            collection_id=COLLECTION_ID,
            user_email="ada@example.com",
        )

    assert predictions == [prediction]
    assert provider.prompts == [PROMPT]
    assert f"Segmented sample {image.sample_id} in" in caplog.text
    (event,) = reported
    assert event.user_email == "ada@example.com"
    assert event.service is usage_reporter.UsageService.AUTOLABELING
    assert event.operation == "segment_interactive"
    assert event.mode is usage_reporter.UsageMode.REALTIME
    assert event.job_id is None
    assert event.vendor == "stub-vendor"
    assert event.model == "stub-model"
    assert event.unit is usage_reporter.UsageUnit.REQUEST
    assert event.quantity == 1
    assert event.success is True
    assert event.collection_id == COLLECTION_ID
    assert event.latency_ms is not None
    assert event.details == {
        "sample_id": "00000000-0000-0000-0000-000000000001",
        "num_predictions": 1,
    }
    assert event.occurred_at.tzinfo is not None


def test_segment__provider_error(mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)
    provider = StubProvider(error=ProviderError("Request timed out."))

    with pytest.raises(ProviderError, match=r"Request timed out\."):
        run_provider.segment(
            provider=provider,
            image=helpers.make_image(width=100, height=50),
            prompt=PROMPT,
            operation=run_provider.OPERATION_INSTANCES,
            collection_id=COLLECTION_ID,
            user_email=None,
        )

    # The vendor can bill a failed call, so it is reported
    (event,) = reported
    assert event.success is False
    assert event.quantity == 1
    assert event.operation == "segment_instances"
    assert event.user_email is None
    assert event.details is not None
    assert event.details["num_predictions"] == 0


@pytest.mark.parametrize(
    "error",
    [
        ProviderNotCalledError("Upload failed."),
        ProviderUnavailableError("No key."),
        NotFoundError("The image file 'a.jpg' could not be read."),
    ],
)
def test_segment__vendor_not_called(error: Exception, mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)
    provider = StubProvider(error=error)

    with pytest.raises(type(error)):
        run_provider.segment(
            provider=provider,
            image=helpers.make_image(width=100, height=50),
            prompt=PROMPT,
            operation=run_provider.OPERATION_INTERACTIVE,
            collection_id=COLLECTION_ID,
            user_email=None,
        )

    assert reported == []


def test_segment__new_event_id_per_call(mocker: MockerFixture) -> None:
    reported = _capture_reports(mocker=mocker)

    for _ in range(2):
        run_provider.segment(
            provider=StubProvider(),
            image=helpers.make_image(width=100, height=50),
            prompt=PROMPT,
            operation=run_provider.OPERATION_INTERACTIVE,
            collection_id=COLLECTION_ID,
            user_email=None,
        )

    assert len(reported) == 2
    assert reported[0].event_id != reported[1].event_id


def _capture_reports(mocker: MockerFixture) -> list[usage_reporter.UsageEvent]:
    reported: list[usage_reporter.UsageEvent] = []

    def _record(events: Sequence[usage_reporter.UsageEvent]) -> None:
        reported.extend(events)

    mocker.patch.object(usage_reporter, "report", side_effect=_record)
    return reported
