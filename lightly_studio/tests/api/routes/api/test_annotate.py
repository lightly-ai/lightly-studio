from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_GATEWAY, HTTP_STATUS_OK
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderError
from lightly_studio.services.assisted_labeling_service import get_active_provider
from lightly_studio.usage import usage_reporter
from tests.helpers_resolvers import create_collection, create_image


@pytest.fixture(autouse=True)
def _use_fake_provider(mocker: MockerFixture) -> None:
    mocker.patch.object(get_active_provider, "get_usable_provider", return_value=FakeProvider())


@pytest.fixture
def reported(mocker: MockerFixture) -> list[usage_reporter.UsageEvent]:
    captured: list[usage_reporter.UsageEvent] = []

    def _record(events: Sequence[usage_reporter.UsageEvent]) -> None:
        captured.extend(events)

    mocker.patch.object(usage_reporter, "report", side_effect=_record)
    return captured


@pytest.fixture
def image_ids(db_session: Session) -> tuple[UUID, UUID]:
    """Returns the collection ID and sample ID of a 100x80 image."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=80
    )
    return collection.collection_id, image.sample_id


@pytest.mark.parametrize(
    ("headers", "expected_user_email"),
    [
        pytest.param({}, None, id="missing"),
        pytest.param({"X-User-Email": "   "}, None, id="blank"),
        pytest.param({"X-User-Email": " ada@example.com "}, "ada@example.com", id="padded"),
    ],
)
def test_create_interactive_annotation_preview__reports_the_forwarded_user_email(
    test_client: TestClient,
    reported: list[usage_reporter.UsageEvent],
    image_ids: tuple[UUID, UUID],
    headers: dict[str, str],
    expected_user_email: str | None,
) -> None:
    collection_id, sample_id = image_ids

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection_id),
            "sample_id": str(sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": True}],
        },
        headers=headers,
    )

    assert response.status_code == HTTP_STATUS_OK
    assert len(reported) == 1
    assert reported[0].user_email == expected_user_email
    assert reported[0].operation == "segment_interactive"


def test_create_interactive_annotation_preview__reports_a_provider_failure(
    test_client: TestClient,
    mocker: MockerFixture,
    reported: list[usage_reporter.UsageEvent],
    image_ids: tuple[UUID, UUID],
) -> None:
    provider = FakeProvider()
    mocker.patch.object(provider, "segment", side_effect=ProviderError("provider is down"))
    mocker.patch.object(get_active_provider, "get_usable_provider", return_value=provider)
    collection_id, sample_id = image_ids

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection_id),
            "sample_id": str(sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": True}],
        },
        headers={"X-User-Email": "ada@example.com"},
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert len(reported) == 1
    assert reported[0].success is False
    assert reported[0].quantity == 1
    assert reported[0].details is not None
    assert reported[0].details["num_predictions"] == 0


def test_create_instances_annotation_preview__reports_usage_with_user_email(
    test_client: TestClient,
    reported: list[usage_reporter.UsageEvent],
    image_ids: tuple[UUID, UUID],
) -> None:
    collection_id, sample_id = image_ids

    response = test_client.post(
        "/api/annotate/instances",
        json={
            "collection_id": str(collection_id),
            "sample_id": str(sample_id),
            "boxes": [{"x": 0.1, "y": 0.125, "width": 0.3, "height": 0.375}],
        },
        headers={"X-User-Email": "ada@example.com"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert len(reported) == 1
    event = reported[0]
    assert event.user_email == "ada@example.com"
    assert event.service is usage_reporter.UsageService.AUTOLABELING
    assert event.operation == "segment_instances"
    assert event.collection_id == collection_id
    assert event.success is True
    assert event.details is not None
    assert event.details["sample_id"] == str(sample_id)
    assert event.details["num_predictions"] == len(response.json()["predictions"])
